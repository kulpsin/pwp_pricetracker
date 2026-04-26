#!/usr/bin/env python3
"""
Tests for the price update queue API endpoints.
"""

import json
import time
from datetime import datetime, timedelta, timezone

import pytest

from pricetracker.models import ApiKey, PriceUpdateJob, Product
from pricetracker.db import db
from pricetracker import cache


# Fixtures for worker/admin users


@pytest.fixture(name="worker_user")
def fixture_worker_user(client):
    """Creates a worker user"""
    email = "new-worker-queue-user@localhost"
    resp = client.post("/api/users/", json={"email": email})
    assert resp.status_code == 201
    key = resp.headers.get('X-Api-Key')
    location = resp.headers.get('Location')
    headers = {'X-Api-Key': key}

    key_hash = ApiKey.key_hash(key)
    a = ApiKey.query.where(ApiKey.key == key_hash).first()
    a.worker = True
    db.session.add(a)
    db.session.commit()

    yield {
        "email": email,
        "key": key,
        "location": location,
        "client": client,
        "headers": headers,
    }

    try:
        client.delete(location, headers=headers)
    except Exception:
        pass


@pytest.fixture(name="admin_user")
def fixture_admin_user(client):
    """Creates an admin user"""
    email = "new-admin-queue-user@localhost"
    resp = client.post("/api/users/", json={"email": email})
    assert resp.status_code == 201
    key = resp.headers.get('X-Api-Key')
    location = resp.headers.get('Location')
    headers = {'X-Api-Key': key}

    key_hash = ApiKey.key_hash(key)
    a = ApiKey.query.where(ApiKey.key == key_hash).first()
    a.admin = True
    db.session.add(a)
    db.session.commit()

    yield {
        "email": email,
        "key": key,
        "location": location,
        "client": client,
        "headers": headers,
    }

    try:
        client.delete(location, headers=headers)
    except Exception:
        pass


@pytest.fixture(name="product_for_queue")
def fixture_product_for_queue(client):
    """Creates a user and a product for queue testing"""
    email = "queue-test-user@localhost"
    resp = client.post("/api/users/", json={"email": email})
    assert resp.status_code == 201
    key = resp.headers.get('X-Api-Key')
    location = resp.headers.get('Location')
    headers = {'X-Api-Key': key}

    # Create a product
    req = {
        "name": "queue-test-product",
        "url": "http://localhost/queue-test-product",
    }
    resp = client.post("/api/products/", json=req, headers=headers)
    assert resp.status_code == 201
    product_location = resp.headers.get('Location')

    # Extract hruid from location URL and query product_id
    hruid = product_location.rstrip('/').split('/')[-1]
    product_id = Product.query.filter_by(hruid=hruid).first().id

    yield {
        "req": req,
        "location": product_location,
        "hruid": hruid,
        "id": product_id,
        "user_email": email,
        "client": client,
        "headers": headers,
    }

    try:
        client.delete(product_location, headers=headers)
        client.delete(location, headers=headers)
    except Exception:
        pass


@pytest.fixture(name="product_for_queue_other_user")
def fixture_product_for_queue_other_user(client):
    """Creates a different user and a product for queue testing (to test owner enforcement)"""
    email = "queue-test-other-user@localhost"
    resp = client.post("/api/users/", json={"email": email})
    assert resp.status_code == 201
    key = resp.headers.get('X-Api-Key')
    location = resp.headers.get('Location')
    headers = {'X-Api-Key': key}

    # Create a product
    req = {
        "name": "queue-test-other-product",
        "url": "http://localhost/queue-test-other-product",
    }
    resp = client.post("/api/products/", json=req, headers=headers)
    assert resp.status_code == 201
    product_location = resp.headers.get('Location')

    hruid = product_location.rstrip('/').split('/')[-1]
    product_id = Product.query.filter_by(hruid=hruid).first().id

    yield {
        "req": req,
        "location": product_location,
        "hruid": hruid,
        "id": product_id,
        "user_email": email,
        "client": client,
        "headers": headers,
    }

    try:
        client.delete(product_location, headers=headers)
        client.delete(location, headers=headers)
    except Exception:
        pass


class TestPriceUpdateJobCollection:
    """Tests for POST /api/products/<product>/update-jobs/ and GET /api/products/<product>/update-jobs/"""

    def test_post_enqueue(self, product_for_queue):
        """Product owner can enqueue a price update job"""
        resp = product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )
        assert resp.status_code == 201
        location = resp.headers.get('Location')
        assert location is not None

    def test_post_enqueue_idempotent(self, product_for_queue):
        """Enqueueing the same product twice returns existing job (200)"""
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )
        resp = product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )
        assert resp.status_code == 200
        # Should return the original job's location
        location = resp.headers.get('Location')
        assert location is not None

    def test_post_enqueue_nonexistent_product(self, product_for_queue):
        """Enqueueing for a non-existent product returns 404"""
        resp = product_for_queue['client'].post(
            "/api/products/nonexistent-product-1/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )
        assert resp.status_code == 404

    def test_post_enqueue_no_auth(self, product_for_queue):
        """Unauthenticated requests are rejected"""
        resp = product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
        )
        assert resp.status_code == 401

    def test_post_enqueue_wrong_user_forbidden(self, product_for_queue, product_for_queue_other_user):
        """Non-owner cannot enqueue for another user's product"""
        resp = product_for_queue['client'].post(
            f"/api/products/{product_for_queue_other_user['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )
        assert resp.status_code == 403

    def test_get_list_public(self, product_for_queue):
        """Anyone can list update jobs for a product (no auth required)"""
        # Create a job first
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )
        resp = product_for_queue['client'].get(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
        )
        assert resp.status_code == 200
        assert len(resp.json) >= 1

    def test_get_list_empty(self, product_for_queue):
        """Empty list when no jobs exist"""
        resp = product_for_queue['client'].get(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
        )
        assert resp.status_code == 200
        assert resp.json == []

    def test_get_list_sorted_by_created_at_desc(self, product_for_queue):
        """Jobs are sorted by created_at descending (newest first)"""
        # Create two jobs with different statuses to avoid unique constraint
        job_a = PriceUpdateJob(
            product_id=product_for_queue['id'],
            status="completed",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        job_b = PriceUpdateJob(
            product_id=product_for_queue['id'],
            status="failed",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        db.session.add(job_a)
        db.session.add(job_b)
        db.session.commit()

        resp = product_for_queue['client'].get(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
        )
        assert resp.status_code == 200
        assert len(resp.json) == 2
        # Newest first: first job's created_at should be >= second job's
        assert resp.json[0]["created_at"] >= resp.json[1]["created_at"]


class TestPriceUpdateJobClaim:
    """Tests for GET /api/price-update-jobs/claim/"""

    def test_claim_returns_job(self, product_for_queue, worker_user):
        """Worker can claim a pending job"""
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )
        resp = worker_user['client'].get(
            "/api/price-update-jobs/claim/",
            headers=worker_user['headers'],
        )
        assert resp.status_code == 200
        assert resp.json["status"] == "processing"
        assert resp.json["product_id"] == product_for_queue['id']

    def test_claim_returns_204_empty(self, worker_user):
        """No pending jobs returns 204"""
        resp = worker_user['client'].get(
            "/api/price-update-jobs/claim/",
            headers=worker_user['headers'],
        )
        assert resp.status_code == 204

    def test_claim_worker_only(self, product_for_queue):
        """Regular user cannot claim jobs"""
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )
        resp = product_for_queue['client'].get(
            "/api/price-update-jobs/claim/",
            headers=product_for_queue['headers'],
        )
        assert resp.status_code == 403

    def test_claim_no_auth(self, product_for_queue):
        """Unauthenticated cannot claim jobs"""
        resp = product_for_queue['client'].get("/api/price-update-jobs/claim/")
        assert resp.status_code == 401

    def test_claim_oldest_first(self, product_for_queue, worker_user):
        """Claim returns the oldest pending job first"""
        # Create a second product for a different product_id
        resp = product_for_queue['client'].post(
            "/api/products/",
            json={"name": "second-product", "url": "http://localhost/second-product"},
            headers=product_for_queue['headers'],
        )
        assert resp.status_code == 201
        second_hruid = resp.headers['Location'].rstrip('/').split('/')[-1]
        second_product_id = Product.query.filter_by(hruid=second_hruid).first().id

        # Enqueue second product first (older job)
        product_for_queue['client'].post(
            f"/api/products/{second_hruid}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )
        # Claim should return the first enqueued product (older job)
        resp = worker_user['client'].get(
            "/api/price-update-jobs/claim/",
            headers=worker_user['headers'],
        )
        assert resp.status_code == 200
        assert resp.json["product_id"] == second_product_id


class TestPriceUpdateJobList:
    """Tests for GET /api/price-update-jobs/"""

    def test_get_list_admin_only(self, product_for_queue, admin_user):
        """Admin can list all jobs"""
        # Create a job first
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )
        resp = admin_user['client'].get(
            "/api/price-update-jobs/",
            headers=admin_user['headers'],
        )
        assert resp.status_code == 200
        assert len(resp.json) >= 1

    def test_get_list_regular_user_forbidden(self, product_for_queue):
        """Regular user cannot list all jobs"""
        resp = product_for_queue['client'].get(
            "/api/price-update-jobs/",
            headers=product_for_queue['headers'],
        )
        assert resp.status_code == 403

    def test_get_list_no_auth(self, product_for_queue):
        """Unauthenticated cannot list all jobs"""
        resp = product_for_queue['client'].get("/api/price-update-jobs/")
        assert resp.status_code == 401

    def test_get_filter_by_status(self, product_for_queue, admin_user):
        """Admin can filter jobs by status"""
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )
        resp = admin_user['client'].get(
            "/api/price-update-jobs/?status=pending",
            headers=admin_user['headers'],
        )
        assert resp.status_code == 200

    def test_get_filter_invalid_status(self, product_for_queue, admin_user):
        """Invalid status filter returns 400"""
        resp = admin_user['client'].get(
            "/api/price-update-jobs/?status=invalid",
            headers=admin_user['headers'],
        )
        assert resp.status_code == 400


class TestPriceUpdateJobItem:
    """Tests for PATCH /api/price-update-jobs/<job_id>/"""

    def test_patch_complete(self, product_for_queue, worker_user):
        """Worker can mark a job as completed"""
        # Enqueue a job
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )

        # Claim it
        resp = worker_user['client'].get(
            "/api/price-update-jobs/claim/",
            headers=worker_user['headers'],
        )
        assert resp.status_code == 200
        job_id = resp.json["id"]

        # Complete it
        resp = worker_user['client'].patch(
            f"/api/price-update-jobs/{job_id}/",
            json={"status": "completed"},
            headers=worker_user['headers'],
        )
        assert resp.status_code == 200
        assert resp.json["status"] == "completed"
        assert resp.json["completed_at"] is not None

    def test_patch_fail(self, product_for_queue, worker_user):
        """Worker can mark a job as failed with error message"""
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )

        resp = worker_user['client'].get(
            "/api/price-update-jobs/claim/",
            headers=worker_user['headers'],
        )
        job_id = resp.json["id"]

        resp = worker_user['client'].patch(
            f"/api/price-update-jobs/{job_id}/",
            json={"status": "failed", "error_message": "Scrape failed"},
            headers=worker_user['headers'],
        )
        assert resp.status_code == 200
        assert resp.json["status"] == "failed"
        assert resp.json["error_message"] == "Scrape failed"

    def test_patch_invalid_status(self, product_for_queue, worker_user):
        """Invalid status returns 400"""
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )

        resp = worker_user['client'].get(
            "/api/price-update-jobs/claim/",
            headers=worker_user['headers'],
        )
        job_id = resp.json["id"]

        resp = worker_user['client'].patch(
            f"/api/price-update-jobs/{job_id}/",
            json={"status": "invalid"},
            headers=worker_user['headers'],
        )
        assert resp.status_code == 400

    def test_patch_not_found(self, worker_user):
        """Non-existent job returns 404"""
        resp = worker_user['client'].patch(
            "/api/price-update-jobs/99999/",
            json={"status": "completed"},
            headers=worker_user['headers'],
        )
        assert resp.status_code == 404

    def test_patch_worker_only(self, product_for_queue):
        """Regular user cannot update jobs"""
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )

        job = PriceUpdateJob.query.filter_by(
            product_id=product_for_queue['id'],
            status="pending",
        ).first()

        if job:
            resp = product_for_queue['client'].patch(
                f"/api/price-update-jobs/{job.id}/",
                json={"status": "completed"},
                headers=product_for_queue['headers'],
            )
            assert resp.status_code == 403

    def test_patch_no_auth(self, product_for_queue):
        """Unauthenticated cannot update jobs"""
        resp = product_for_queue['client'].patch(
            "/api/price-update-jobs/1/",
            json={"status": "completed"},
        )
        assert resp.status_code == 401

    def test_patch_wrong_mediatype(self, product_for_queue, worker_user):
        """Only JSON mediatype allowed"""
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )

        resp = worker_user['client'].get(
            "/api/price-update-jobs/claim/",
            headers=worker_user['headers'],
        )
        job_id = resp.json["id"]

        resp = worker_user['client'].patch(
            f"/api/price-update-jobs/{job_id}/",
            data=json.dumps({"status": "completed"}),
            headers=worker_user['headers'],
        )
        assert resp.status_code == 415

    def test_get_job_admin_only(self, product_for_queue, admin_user):
        """Admin can get a specific job"""
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )

        job = PriceUpdateJob.query.filter_by(
            product_id=product_for_queue['id'],
        ).first()
        assert job is not None

        resp = admin_user['client'].get(
            f"/api/price-update-jobs/{job.id}/",
            headers=admin_user['headers'],
        )
        assert resp.status_code == 200
        assert resp.json["product_id"] == product_for_queue['id']

    def test_get_job_regular_user_forbidden(self, product_for_queue):
        """Regular user cannot get a specific job"""
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )

        job = PriceUpdateJob.query.filter_by(
            product_id=product_for_queue['id'],
        ).first()
        assert job is not None

        resp = product_for_queue['client'].get(
            f"/api/price-update-jobs/{job.id}/",
            headers=product_for_queue['headers'],
        )
        assert resp.status_code == 403

    def test_patch_no_product_id_required(self, product_for_queue, worker_user):
        """PATCH body does not require product_id"""
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )

        resp = worker_user['client'].get(
            "/api/price-update-jobs/claim/",
            headers=worker_user['headers'],
        )
        job_id = resp.json["id"]

        # PATCH without product_id should work
        resp = worker_user['client'].patch(
            f"/api/price-update-jobs/{job_id}/",
            json={"status": "completed"},
            headers=worker_user['headers'],
        )
        assert resp.status_code == 200

    def test_cache_invalidated_on_complete(self, product_for_queue, worker_user):
        """Cache is cleared when a job is completed"""
        product_for_queue['client'].post(
            f"/api/products/{product_for_queue['hruid']}/update-jobs/",
            json={},
            headers=product_for_queue['headers'],
        )

        resp = worker_user['client'].get(
            "/api/price-update-jobs/claim/",
            headers=worker_user['headers'],
        )
        job_id = resp.json["id"]

        # Pre-populate cache
        resp = product_for_queue['client'].get(
            product_for_queue['location'],
        )
        assert resp.status_code == 200

        # Complete the job (should clear cache)
        resp = worker_user['client'].patch(
            f"/api/price-update-jobs/{job_id}/",
            json={"status": "completed"},
            headers=worker_user['headers'],
        )
        assert resp.status_code == 200

        # Cache should be cleared
        assert cache.cache._cache == {}


class TestStaleJobRecovery:
    """Tests for stale job re-queueing during claim"""

    def test_stale_jobs_requeued(self, product_for_queue, worker_user):
        """Jobs stuck in processing for >5 min should be re-queued as pending"""
        # Create a job and manually set it as stale
        job = PriceUpdateJob(
            product_id=product_for_queue['id'],
            status="processing",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        db.session.add(job)
        db.session.commit()

        # Claim should re-queue stale jobs first, then claim the newly available one
        resp = worker_user['client'].get(
            "/api/price-update-jobs/claim/",
            headers=worker_user['headers'],
        )
        assert resp.status_code == 200
        assert resp.json["id"] == job.id
        assert resp.json["status"] == "processing"

    def test_claim_no_jobs_after_stale_requeue_empty(self, product_for_queue, worker_user):
        """After reclaiming stale jobs and claiming one, 204 if nothing left"""
        # Create a stale job
        job = PriceUpdateJob(
            product_id=product_for_queue['id'],
            status="processing",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        db.session.add(job)
        db.session.commit()

        # First claim re-queues stale and claims it
        resp = worker_user['client'].get(
            "/api/price-update-jobs/claim/",
            headers=worker_user['headers'],
        )
        assert resp.status_code == 200

        # Second claim should return 204
        resp = worker_user['client'].get(
            "/api/price-update-jobs/claim/",
            headers=worker_user['headers'],
        )
        assert resp.status_code == 204

from datetime import datetime, timedelta, timezone

from flask import Response, request, url_for
from flask_restful import Resource
from jsonschema import ValidationError, validate
from werkzeug.exceptions import BadRequest, NotFound, Forbidden, Unauthorized

from .. import models
from ..db import db
from .. import auth, cache


class PriceUpdateJobCollection(Resource):

    @auth.require(owner=True)
    def post(self, product):
        """Enqueue a price update job for a specific product.
        Idempotent — will not create duplicate pending jobs for the same product.
        ---
        security:
            - api_key: []
        parameters:
            - $ref: '#/components/parameters/product'
        responses:
            '201':
                description: Price update job created
            '401':
                description: Authentication required
            '403':
                description: Owner access required
            '404':
                description: Product not found
            '409':
                description: A pending or processing job already exists for this product
        """
        product_id = product.id

        # Check for existing pending/processing jobs (idempotent)
        existing = models.PriceUpdateJob.query.filter_by(
            product_id=product_id,
            status="pending",
        ).first()
        if existing is None:
            existing = models.PriceUpdateJob.query.filter_by(
                product_id=product_id,
                status="processing",
            ).first()

        if existing is not None:
            return Response(
                status=200,
                headers={
                    "Location": url_for('api.priceupdatejobitem', job_id=existing.id),
                },
            )

        job = models.PriceUpdateJob(
            product_id=product_id,
            status="pending",
            url=product.url,
        )
        db.session.add(job)
        db.session.commit()

        return Response(
            status=201,
            headers={
                "Location": url_for('api.priceupdatejobitem', job_id=job.id),
            },
        )

    @cache.cached(timeout=60)
    def get(self, product):
        """List all price update jobs for this product.
        ---
        security: []
        parameters:
            - $ref: '#/components/parameters/product'
        responses:
            '200':
                description: List of price update jobs for this product
                content:
                    application/json:
                        schema:
                            type: array
                            items:
                                $ref: '#/components/schemas/PriceUpdateJob'
        """
        jobs = models.PriceUpdateJob.query.filter_by(
            product_id=product.id,
        ).order_by(
            models.PriceUpdateJob.created_at.desc(),
        ).all()

        return [job.serialize() for job in jobs], 200


class PriceUpdateJobClaim(Resource):

    @auth.require(worker=True)
    def get(self):
        """Atomically claim the oldest pending price update job.
        Uses optimistic locking: a single UPDATE marks the oldest pending
        job as processing. If no rows are affected, no jobs are available.
        This is atomic in SQLite — only one worker can match the subquery.
        Returns the claimed job or 204 if no pending jobs are available.
        ---
        security:
            - api_key: []
        responses:
            '200':
                description: A claimed price update job
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/PriceUpdateJob'
            '204':
                description: No pending jobs available
            '401':
                description: Authentication required
            '403':
                description: Worker access required
        """
        # Reclaim stale processing jobs (worker crashed mid-processing)
        stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
        models.PriceUpdateJob.query.filter(
            models.PriceUpdateJob.status == "processing",
            models.PriceUpdateJob.started_at < stale_threshold,
        ).update(
            {"status": "pending", "started_at": None},
            synchronize_session="fetch",
        )
        db.session.commit()

        # Atomic claim: find the oldest pending job and mark it as processing.
        # In SQLite, this is atomic — only one worker can match and update
        # the same row. If no pending jobs exist, return 204.
        job = models.PriceUpdateJob.query.filter_by(
            status="pending",
        ).order_by(
            models.PriceUpdateJob.created_at.asc()
        ).first()

        if job is None:
            return Response(status=204)

        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        db.session.commit()

        return job.serialize(), 200


class PriceUpdateJobList(Resource):

    @auth.require(admin=True)
    def get(self):
        """List all price update jobs (admin only).
        ---
        security:
            - api_key: []
        parameters:
          - name: status
            in: query
            type: string
            enum: [pending, processing, completed, failed]
        responses:
            '200':
                description: List of price update jobs
                content:
                    application/json:
                        schema:
                            type: array
                            items:
                                $ref: '#/components/schemas/PriceUpdateJob'
            '401':
                description: Authentication required
            '403':
                description: Admin access required
            '400':
                description: Invalid status filter
        """
        status_filter = request.args.get("status")
        if status_filter:
            if status_filter not in ("pending", "processing", "completed", "failed"):
                raise BadRequest("Invalid status filter")
            jobs = models.PriceUpdateJob.query.filter_by(status=status_filter).all()
        else:
            jobs = models.PriceUpdateJob.query.order_by(
                models.PriceUpdateJob.created_at.desc()
            ).all()

        return [job.serialize() for job in jobs], 200


class PriceUpdateJobItem(Resource):

    @auth.require(worker=True)
    def patch(self, job_id):
        """Complete or fail a claimed price update job.
        ---
        security:
            - api_key: []
        parameters:
          - name: job_id
            in: path
            required: true
            schema:
                type: integer
          - name: body
            in: body
            required: true
            schema:
                $ref: '#/components/schemas/PriceUpdateJob'
        responses:
            '200':
                description: Job status updated
            '400':
                description: Invalid status or request body
            '401':
                description: Authentication required
            '403':
                description: Worker access required
            '404':
                description: Job not found
        """
        if not request.is_json:
            return "Request content type must be JSON", 415

        try:
            validate(request.json, models.PriceUpdateJob.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        job = db.session.get(models.PriceUpdateJob, job_id)
        if job is None:
            raise NotFound("Job not found")

        new_status = request.json.get("status")
        if new_status not in ("completed", "failed"):
            raise BadRequest("Status must be 'completed' or 'failed'")

        if job.status == new_status:
            return job.serialize(), 200

        job.status = new_status
        job.completed_at = datetime.now(timezone.utc)
        if "error_message" in request.json:
            job.error_message = request.json["error_message"]
        if "price_value" in request.json:
            job.price_value = request.json["price_value"]

        # When completed with a price, store it as a Price record
        if new_status == "completed" and job.price_value is not None:
            new_price = models.Price(
                product_id=job.product_id,
                value=job.price_value,
                timestamp=datetime.now(timezone.utc),
            )
            db.session.add(new_price)

        db.session.commit()

        # Invalidate cache so API serves fresh data after price updates
        if new_status == "completed":
            cache.clear()

        return job.serialize(), 200

    @auth.require(admin=False, worker=False, owner=False)
    def get(self, job_id):
        """Get details of a specific job (admin only).
        ---
        security:
            - api_key: []
        parameters:
          - name: job_id
            in: path
            required: true
            schema:
                type: integer
        responses:
            '200':
                description: Job details
            '401':
                description: Authentication required
            '403':
                description: Admin access required
            '404':
                description: Job not found
        """
        job = db.session.get(models.PriceUpdateJob, job_id)
        if job is None:
            raise NotFound("Job not found")

        if "X-Api-Key" not in request.headers:
            raise Unauthorized

        key_hash = models.ApiKey.key_hash(request.headers.get("X-Api-Key").strip())
        db_key = models.ApiKey.query.where(models.ApiKey.key == key_hash).first()

        if db_key is None:
            raise Forbidden

        if not db_key.admin:
            raise Forbidden

        return job.serialize(), 200

#!/usr/bin/env python3
"""
Tests for the distributed worker process (worker/app.py).
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

# Set required env var before importing worker.app
os.environ.setdefault("WORKER_API_KEY", "test-worker-key")
os.environ.setdefault("API_BASE_URL", "http://localhost:5000")


@pytest.fixture(autouse=True)
def _reload_worker():
    """Reload worker.app to ensure clean state between tests."""
    # Clear all worker modules
    mods_to_remove = [k for k in sys.modules if k.startswith("worker")]
    for mod in mods_to_remove:
        del sys.modules[mod]
    yield
    # Clean up after test
    mods_to_remove = [k for k in sys.modules if k.startswith("worker")]
    for mod in mods_to_remove:
        del sys.modules[mod]


class TestClaimJob:

    def test_claim_job_returns_data(self):
        """claim_job returns the parsed JSON when API returns 200"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 42, "url": "http://example.com", "status": "pending"}

        with patch("worker.app.requests") as mock_requests:
            mock_requests.get.return_value = mock_response
            import worker.app
            result = worker.app.claim_job()

        assert result == {"id": 42, "url": "http://example.com", "status": "pending"}
        mock_requests.get.assert_called_once()
        call_url = mock_requests.get.call_args[0][0]
        assert "/api/price-update-jobs/claim/" in call_url

    def test_claim_job_returns_none_on_204(self):
        """claim_job returns None when API returns 204 (no pending jobs)"""
        mock_response = MagicMock()
        mock_response.status_code = 204

        with patch("worker.app.requests") as mock_requests:
            mock_requests.get.return_value = mock_response
            import worker.app
            result = worker.app.claim_job()

        assert result is None

    def test_claim_job_raises_on_error(self):
        """claim_job raises on non-success status codes"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server error")

        with patch("worker.app.requests") as mock_requests:
            mock_requests.get.return_value = mock_response
            import worker.app
            with pytest.raises(Exception):
                worker.app.claim_job()


class TestCompleteJob:

    def test_complete_job_success(self):
        """complete_job returns parsed JSON on success"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 42, "status": "completed", "price_value": 299.99}

        with patch("worker.app.requests") as mock_requests:
            mock_requests.patch.return_value = mock_response
            import worker.app
            result = worker.app.complete_job(42, 299.99)

        assert result == {"id": 42, "status": "completed", "price_value": 299.99}
        mock_requests.patch.assert_called_once()
        call_kwargs = mock_requests.patch.call_args[1]
        payload = call_kwargs["json"]
        assert payload["status"] == "completed"
        assert payload["price_value"] == 299.99

    def test_complete_job_raises_on_error(self):
        """complete_job raises on non-success status codes"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("Not found")

        with patch("worker.app.requests") as mock_requests:
            mock_requests.patch.return_value = mock_response
            import worker.app
            with pytest.raises(Exception):
                worker.app.complete_job(999, 10.0)


class TestFailJob:

    def test_fail_job_success(self):
        """fail_job returns parsed JSON on success"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 42, "status": "failed"}

        with patch("worker.app.requests") as mock_requests:
            mock_requests.patch.return_value = mock_response
            import worker.app
            result = worker.app.fail_job(42, "Scrape failed")

        assert result == {"id": 42, "status": "failed"}
        mock_requests.patch.assert_called_once()
        call_kwargs = mock_requests.patch.call_args[1]
        payload = call_kwargs["json"]
        assert payload["status"] == "failed"
        assert payload["error_message"] == "Scrape failed"

    def test_fail_job_raises_on_error(self):
        """fail_job raises on non-success status codes"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server error")

        with patch("worker.app.requests") as mock_requests:
            mock_requests.patch.return_value = mock_response
            import worker.app
            with pytest.raises(Exception):
                worker.app.fail_job(42, "Error")


class TestProcessJob:

    def test_process_job_calls_extractor_and_completes(self):
        """process_job calls PriceExtractor.run() and completes the job"""
        mock_extractor = MagicMock()
        mock_extractor.run.return_value = 49.99

        with patch("worker.app.PriceExtractor", return_value=mock_extractor):
            with patch("worker.app.complete_job") as mock_complete:
                import worker.app
                worker.app.process_job({
                    "id": 1,
                    "url": "http://example.com/product",
                    "status": "processing",
                })

        mock_extractor.run.assert_called_once_with("http://example.com/product")
        mock_complete.assert_called_once_with(1, 49.99)

    def test_process_job_propagates_extractor_exception(self):
        """process_job propagates exceptions from PriceExtractor"""
        mock_extractor = MagicMock()
        mock_extractor.run.side_effect = ValueError("Page not found")

        with patch("worker.app.PriceExtractor", return_value=mock_extractor):
            import worker.app
            with pytest.raises(ValueError):
                worker.app.process_job({
                    "id": 1,
                    "url": "http://example.com/broken",
                    "status": "processing",
                })

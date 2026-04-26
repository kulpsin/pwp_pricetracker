"""
Distributed price update worker.

Polls the main API for pending price update jobs, scrapes the product page
using LLM vision/text analysis, and completes the job with the extracted price.

Environment variables:
    API_BASE_URL      - Main API URL (e.g. http://app:8000)
    WORKER_API_KEY    - Worker API key for authentication
    OPENAI_API_KEY    - Optional: OpenAI-compatible API key (highest priority)
    OPENAI_BASE_URL   - Optional: Custom OpenAI-compatible endpoint (default: https://api.openai.com/v1)
    OPENAI_MODEL      - Optional: Model name to use (default: google/gemma-4-31b-it:free)
    OPENROUTER_API_KEY - Optional: OpenRouter API key for LLM access
"""

import os
import sys
import time

import requests

sys.tracebacklimit = 0

from worker.extractor import PriceExtractor

API = os.environ.get("API_BASE_URL", "http://localhost:8000")
KEY = os.environ.get("WORKER_API_KEY")
HEADERS = {
    "X-Api-Key": KEY,
    "Content-Type": "application/json",
}

if not KEY:
    raise ValueError("WORKER_API_KEY environment variable is required")


def claim_job():
    """Claim the oldest pending price update job."""
    r = requests.get(f"{API}/api/price-update-jobs/claim/", headers=HEADERS, timeout=30)
    if r.status_code == 204:
        return None
    r.raise_for_status()
    return r.json()


def complete_job(job_id, price):
    """Mark a job as completed with the extracted price."""
    r = requests.patch(
        f"{API}/api/price-update-jobs/{job_id}/",
        json={"status": "completed", "price_value": price},
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def fail_job(job_id, error_message):
    """Mark a job as failed with an error message."""
    r = requests.patch(
        f"{API}/api/price-update-jobs/{job_id}/",
        json={"status": "failed", "error_message": error_message},
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def process_job(job):
    """Scrape the product URL and extract the price."""
    url = job["url"]
    print(f"Processing job {job['id']} for {url}")

    extractor = PriceExtractor()
    price = extractor.run(url)

    print(f"Extracted price: {price:.2f}")
    complete_job(job["id"], price)
    print(f"Job {job['id']} completed with price {price:.2f}")


def main():
    print(f"Worker started, polling {API}/api/price-update-jobs/claim/")
    print(f"Using extractor method based on available LLM backends")

    while True:
        try:
            job = claim_job()
            if job is None:
                time.sleep(2)
                continue

            process_job(job)
        except requests.exceptions.RequestException as e:
            print(f"API connection error: {e}")
            time.sleep(5)
        except Exception as e:
            print(f"Error processing job: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()

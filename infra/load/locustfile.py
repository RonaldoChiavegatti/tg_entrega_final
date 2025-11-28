import json
import os
from locust import HttpUser, between, task

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
TENANT = os.getenv("TENANT", "demo")
DOC_ID = os.getenv("DOC_ID", "demo-doc")
YEAR = int(os.getenv("YEAR", "2024"))
AUTHORIZATION = os.getenv("AUTHORIZATION")


def _headers():
    headers = {"Content-Type": "application/json"}
    if AUTHORIZATION:
        headers["Authorization"] = AUTHORIZATION
    return headers


class ApiUser(HttpUser):
    wait_time = between(1, 2)
    host = BASE_URL

    @task
    def upload_patch_recalc(self):
        key = f"locust/{DOC_ID}.txt"
        presign_payload = {"key": key, "content_type": "text/plain", "tenant_id": TENANT}
        with self.client.post(
            "/documents/storage/presign-upload",
            data=json.dumps(presign_payload),
            headers=_headers(),
            name="presign-upload",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Unexpected status {resp.status_code}")

        patch_payload = [
            {"path": "totals.gross_amount", "value": 123.45, "source": "locust"},
            {"path": "storage.mock_text", "value": "patched via locust", "source": "locust"},
        ]
        with self.client.patch(
            f"/documents/{DOC_ID}",
            data=json.dumps(patch_payload),
            headers=_headers(),
            name="documents-patch",
            catch_response=True,
        ) as resp:
            if resp.status_code not in (200, 404):
                resp.failure(f"Unexpected status {resp.status_code}")

        recalc_payload = {"tenant_id": TENANT, "year": YEAR, "doc_ids": [DOC_ID]}
        with self.client.post(
            "/limits/recalculate",
            data=json.dumps(recalc_payload),
            headers=_headers(),
            name="limits-recalc",
            catch_response=True,
        ) as resp:
            if resp.status_code not in (200, 202):
                resp.failure(f"Unexpected status {resp.status_code}")

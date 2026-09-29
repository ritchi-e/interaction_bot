import httpx

from apps.calls.dograh import DograhClient, DograhError, extract_run_id


class DograhAdmin(DograhClient):
    def create_workflow(self, name, definition):
        return self._json("POST", "/api/v1/workflow/create/definition", {"name": name, "workflow_definition": definition})

    def update_workflow(self, workflow_id, name, definition):
        return self._json(
            "PUT",
            f"/api/v1/workflow/{workflow_id}",
            {"name": name, "workflow_definition": definition},
        )

    def _json(self, method, path, body):
        if not self.api_key:
            raise DograhError("Dograh API key is not configured")
        response = httpx.request(
            method,
            self.base_url + path,
            json=body,
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            timeout=30.0,
        )
        if response.status_code >= 400:
            raise DograhError("Dograh rejected the agent", response.status_code, response.text[:500])
        payload = response.json() if response.content else {}
        workflow_id = payload.get("id") or payload.get("workflow_id")
        workflow_uuid = str(payload.get("uuid") or payload.get("workflow_uuid") or "")
        if not workflow_uuid and isinstance(payload.get("workflow"), dict):
            workflow_id = workflow_id or payload["workflow"].get("id")
            workflow_uuid = str(payload["workflow"].get("uuid") or "")
        return {"id": workflow_id, "uuid": workflow_uuid, "raw": payload, "run_id": extract_run_id(payload)}

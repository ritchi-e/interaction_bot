import httpx

from apps.calls.dograh import DograhClient, DograhError, extract_run_id


class DograhAdmin(DograhClient):
    def create_workflow(self, name, definition, workflow_configurations=None):
        result = self._json(
            "POST", "/api/v1/workflow/create/definition", {"name": name, "workflow_definition": definition}
        )
        if workflow_configurations and result.get("id"):
            self._configure_workflow(result["id"], workflow_configurations)
        return result

    def update_workflow(self, workflow_id, name, definition, workflow_configurations=None):
        result = self._json(
            "PUT",
            f"/api/v1/workflow/{workflow_id}",
            {"name": name, "workflow_definition": definition},
        )
        if workflow_configurations:
            self._configure_workflow(workflow_id, workflow_configurations)
        return result

    def release_workflow(self, workflow_id):
        """Release the saved draft and return the public workflow uuid.

        Dograh runs only a published version. The create response does not
        include workflow_uuid; the fetch endpoint does.
        """

        fetched = self._request("GET", f"/api/v1/workflow/fetch/{workflow_id}")
        self._request("POST", f"/api/v1/workflow/{workflow_id}/publish")
        return str(fetched.get("workflow_uuid") or "")

    def _configure_workflow(self, workflow_id, workflow_configurations):
        # Dograh takes `workflow_configurations` (e.g. model_overrides for
        # per-campaign STT language / TTS voice) as its own PUT, separate
        # from the workflow_definition PUT above. Same two-step pattern as
        # the local viva tester.
        self._json(
            "PUT",
            f"/api/v1/workflow/{workflow_id}",
            {"workflow_configurations": workflow_configurations},
        )

    def save_plivo_line(self, *, name, auth_id, auth_token, caller_id, config_id=None, phone_number_id=None):
        """Create or update the org's Plivo telephony configuration and caller ID.

        Dograh places the outbound call. Plivo is the phone network. Phone
        numbers are a separate resource from the credentials.
        """

        config = {"provider": "plivo", "auth_id": auth_id, "auth_token": auth_token}
        if config_id:
            saved = self._request(
                "PUT",
                f"/api/v1/organizations/telephony-configs/{config_id}",
                {"name": name, "config": config},
            )
        else:
            saved = self._request(
                "POST",
                "/api/v1/organizations/telephony-configs",
                {"name": name, "is_default_outbound": True, "config": config},
            )
        saved_id = saved.get("id") or config_id
        if phone_number_id or not saved_id:
            return {"config_id": saved_id, "phone_number_id": phone_number_id}
        number = self._request(
            "POST",
            f"/api/v1/organizations/telephony-configs/{saved_id}/phone-numbers",
            {
                "address": caller_id,
                "country_code": "IN",
                "label": "Caller ID",
                "is_default_caller_id": True,
            },
        )
        return {"config_id": saved_id, "phone_number_id": number.get("id")}

    def set_model_configuration(self, config):
        """PUT the shared org's base model configuration (v2/BYOK shape).

        Every business's workflow currently authenticates with the same
        platform API key, so they all share this one org-level base config.
        Per-campaign differences (STT language, TTS voice/provider) travel
        separately as workflow_configurations.model_overrides instead — see
        apps/agents/model_overrides.py.
        """
        return self._request("PUT", "/api/v1/organizations/model-configurations/v2", config)

    def _request(self, method, path, body=None):
        if not self.api_key:
            raise DograhError("Dograh API key is not configured")
        kwargs = {
            "headers": {"X-API-Key": self.api_key, "Content-Type": "application/json"},
            "timeout": 30.0,
        }
        if body is not None:
            kwargs["json"] = body
        response = httpx.request(method, self.base_url + path, **kwargs)
        if response.status_code >= 400:
            detail = ""
            try:
                payload = response.json()
                if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
                    detail = payload["detail"]
            except ValueError:
                detail = ""
            raise DograhError(detail or "Dograh rejected the request", response.status_code, response.text[:500])
        return response.json() if response.content else {}

    def _json(self, method, path, body):
        payload = self._request(method, path, body)
        workflow_id = payload.get("id") or payload.get("workflow_id")
        workflow_uuid = str(payload.get("uuid") or payload.get("workflow_uuid") or "")
        if not workflow_uuid and isinstance(payload.get("workflow"), dict):
            workflow_id = workflow_id or payload["workflow"].get("id")
            workflow_uuid = str(payload["workflow"].get("uuid") or "")
        return {"id": workflow_id, "uuid": workflow_uuid, "raw": payload, "run_id": extract_run_id(payload)}

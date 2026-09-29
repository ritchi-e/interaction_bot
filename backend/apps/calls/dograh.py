import httpx
from django.conf import settings


class DograhError(Exception):
    def __init__(self, message, status_code=None, body=""):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class DograhClient:
    def __init__(self, base_url=None, api_key=None):
        self.base_url = (base_url or settings.DOGRAH_API_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.DOGRAH_API_KEY

    def initiate_call(
        self,
        *,
        phone_number,
        initial_context,
        workflow_uuid="",
        trigger_uuid="",
        from_phone_number_id="",
        telephony_configuration_id="",
    ):
        if not self.api_key:
            raise DograhError("Dograh API key is not configured")
        if trigger_uuid:
            path = f"/api/v1/public/agent/{trigger_uuid}"
        elif workflow_uuid:
            path = f"/api/v1/public/agent/workflow/{workflow_uuid}"
        else:
            raise DograhError("Campaign has no Dograh workflow id")

        body = {"phone_number": phone_number, "initial_context": initial_context}
        if from_phone_number_id:
            body["from_phone_number_id"] = from_phone_number_id
        if telephony_configuration_id:
            body["telephony_configuration_id"] = telephony_configuration_id

        response = httpx.post(
            self.base_url + path,
            json=body,
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            timeout=20.0,
        )
        if response.status_code >= 400:
            raise DograhError("Dograh rejected the call", response.status_code, response.text[:500])
        payload = response.json() if response.content else {}
        return {"run_id": extract_run_id(payload), "raw": payload}


def extract_run_id(payload):
    if not isinstance(payload, dict):
        return ""
    for key in ("run_id", "id"):
        if payload.get(key):
            return str(payload[key])
    for nested in ("run", "data"):
        inner = payload.get(nested)
        if isinstance(inner, dict):
            found = extract_run_id(inner)
            if found:
                return found
    return ""

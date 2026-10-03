import hashlib
import hmac
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from rest_framework.test import APIClient

from apps.calls.models import CallRequest
from apps.campaigns.models import Campaign, OutboundTemplateMessage
from apps.compliance.models import OptOut
from apps.tenants.services import create_organisation

IST = ZoneInfo("Asia/Kolkata")


def _sign(secret, body):
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return "sha256=" + digest


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def org(db):
    user = create_organisation("Sundaram Loans", "ops@sundaram.test", "supersecret1")
    whatsapp = user.organisation.whatsapp
    whatsapp.phone_number_id = "12345"
    whatsapp.waba_id = "67890"
    whatsapp.access_token = "wa-token"
    whatsapp.app_secret = "app-secret"
    whatsapp.save()
    line = user.organisation.plivo
    line.auth_id = "MA_TEST"
    line.auth_token = "token"
    line.caller_id = "+919800000000"
    line.dograh_config_id = 1
    line.save()
    campaign = Campaign.objects.create(
        organisation=user.organisation,
        name="Loan offer",
        language="hi",
        is_default=True,
        dograh_workflow_uuid="workflow-1",
    )
    campaign.context.offer_details = "Processing fee is Rs 499."
    campaign.context.save()
    campaign.keywords.create(keyword="loan")
    return user.organisation


def _payload(message_id="wamid.IN.1", body="Yes loan", context_id="", button=""):
    message = {
        "from": "919876543210",
        "id": message_id,
        "timestamp": "1700000000",
        "type": "text",
        "text": {"body": body},
    }
    if context_id:
        message["context"] = {"id": context_id}
    if button:
        message = {
            "from": "919876543210",
            "id": message_id,
            "type": "interactive",
            "interactive": {"type": "button_reply", "button_reply": {"id": button, "title": "Interested"}},
        }
    return {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"contacts": [{"profile": {"name": "Asha"}}], "messages": [message]}}]}],
    }


def _post(client, org, payload):
    raw = json.dumps(payload).encode()
    return client.post(
        f"/webhooks/whatsapp/{org.slug}/",
        data=raw,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=_sign("app-secret", raw),
    )


@pytest.mark.django_db
def test_verify_challenge(client, org):
    token = org.whatsapp.verify_token
    response = client.get(
        f"/webhooks/whatsapp/{org.slug}/",
        {"hub.mode": "subscribe", "hub.verify_token": token, "hub.challenge": "12345"},
    )
    assert response.status_code == 200
    assert response.content == b"12345"


@pytest.mark.django_db
def test_rejects_bad_signature(client, org):
    response = client.post(
        f"/webhooks/whatsapp/{org.slug}/",
        data=b"{}",
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256="sha256=deadbeef",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_reply_places_one_call(client, org, monkeypatch):
    monkeypatch.setattr(
        "apps.compliance.window.now_ist", lambda: datetime(2026, 9, 28, 11, 0, tzinfo=IST)
    )
    calls = {}

    def fake_initiate(self, **kwargs):
        calls["kwargs"] = kwargs
        return {"run_id": "run-1", "raw": {"id": "run-1"}}

    monkeypatch.setattr("apps.calls.dograh.DograhClient.initiate_call", fake_initiate)
    other = Campaign.objects.create(organisation=org, name="Festive", is_active=True)
    OutboundTemplateMessage.objects.create(campaign=other, wa_message_id="wamid.OUT.1", phone_e164="+919876543210")

    payload = _payload(context_id="wamid.OUT.1", body="tell me more")
    first = _post(client, org, payload)
    second = _post(client, org, payload)

    assert first.status_code == 200
    assert first.json()["accepted"] == 1
    assert second.json()["accepted"] == 0
    assert CallRequest.objects.count() == 1
    call = CallRequest.objects.get()
    assert call.campaign_id == other.id
    assert call.status == "in_progress"
    assert call.lead.name == "Asha"
    assert calls["kwargs"]["phone_number"] == "+919876543210"
    assert calls["kwargs"]["telephony_configuration_id"] == "1"


@pytest.mark.django_db
def test_button_and_keyword_and_default(client, org, monkeypatch):
    monkeypatch.setattr(
        "apps.compliance.window.now_ist", lambda: datetime(2026, 9, 28, 11, 0, tzinfo=IST)
    )
    monkeypatch.setattr(
        "apps.calls.dograh.DograhClient.initiate_call",
        lambda self, **kwargs: {"run_id": "run", "raw": {}},
    )
    default = Campaign.objects.get(organisation=org, is_default=True)
    specific = Campaign.objects.create(organisation=org, name="Cards", dograh_workflow_uuid="wf-2")

    button = _post(client, org, _payload(message_id="m-button", button=f"campaign:{specific.id}"))
    assert button.status_code == 200
    assert CallRequest.objects.get(source_message_id="m-button").campaign_id == specific.id

    keyword = _post(client, org, _payload(message_id="m-key", body="I want a loan"))
    assert CallRequest.objects.get(source_message_id="m-key").campaign_id == default.id


@pytest.mark.django_db
def test_stop_opts_out_and_does_not_call(client, org, monkeypatch):
    monkeypatch.setattr(
        "apps.calls.dograh.DograhClient.initiate_call",
        lambda self, **kwargs: (_ for _ in ()).throw(AssertionError("should not dial")),
    )
    response = _post(client, org, _payload(message_id="m-stop", body="STOP"))
    assert response.status_code == 200
    assert OptOut.objects.filter(phone_e164="+919876543210").exists()
    assert CallRequest.objects.count() == 0


@pytest.mark.django_db
def test_night_reply_waits_for_the_calling_window(client, org, monkeypatch):
    monkeypatch.setattr(
        "apps.compliance.window.now_ist", lambda: datetime(2026, 9, 28, 22, 15, tzinfo=IST)
    )
    monkeypatch.setattr(
        "apps.calls.dograh.DograhClient.initiate_call",
        lambda self, **kwargs: (_ for _ in ()).throw(AssertionError("should wait")),
    )
    response = _post(client, org, _payload(message_id="m-night", body="hello"))
    assert response.status_code == 200
    call = CallRequest.objects.get()
    assert call.status == "pending_window"

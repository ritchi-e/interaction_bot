import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.calls.models import CallRequest
from apps.calls.tasks import dispatch_due_calls
from apps.campaigns.models import Campaign
from apps.compliance.models import CallPermission, OptOut
from apps.tenants.services import create_organisation

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def ready(db):
    user = create_organisation("Sundaram Loans", "ops@sundaram.test", "supersecret1")
    org = user.organisation
    org.whatsapp.phone_number_id = "12345"
    org.whatsapp.access_token = "wa-token"
    org.whatsapp.app_secret = "app-secret"
    org.whatsapp.save()
    line = org.plivo
    line.auth_id = "MA_TEST"
    line.auth_token = "token"
    line.caller_id = "+919800000000"
    line.dograh_config_id = 1
    line.save()
    campaign = Campaign.objects.create(
        organisation=org, name="Offer", is_default=True, dograh_workflow_uuid="workflow-1", language="en_in"
    )
    campaign.context.handoff_message = "I don't have that. A person will call you."
    campaign.context.offer_details = "The fee is Rs 499."
    campaign.context.save()
    return user, org, campaign


@pytest.mark.django_db
def test_rate_limit_blocks_second_call(ready, monkeypatch):
    user, org, campaign = ready
    monkeypatch.setattr(
        "apps.compliance.window.now_ist", lambda: datetime(2026, 9, 28, 11, 0, tzinfo=IST)
    )
    monkeypatch.setattr(
        "apps.calls.dograh.DograhClient.initiate_call",
        lambda self, **kwargs: {"run_id": "run-1", "raw": {"id": "run-1"}},
    )
    from apps.calls.models import Lead
    from apps.calls.services import apply_decision

    CallPermission.objects.create(organisation=org, phone_e164="+919876543210", is_permanent=True)
    lead = Lead.objects.create(organisation=org, phone_e164="+919876543210", campaign=campaign, name="Asha")
    first = CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign)
    apply_decision(first)
    second = CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign)
    apply_decision(second)
    second.refresh_from_db()
    assert second.status == "skipped"
    assert second.skip_reason == "rate_limited"


@pytest.mark.django_db
def test_opt_out_blocks_dial(ready):
    user, org, campaign = ready
    from apps.calls.models import Lead
    from apps.calls.services import apply_decision

    OptOut.objects.create(organisation=org, phone_e164="+919876543210")
    lead = Lead.objects.create(organisation=org, phone_e164="+919876543210", campaign=campaign)
    call = CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign)
    apply_decision(call)
    call.refresh_from_db()
    assert call.status == "skipped"
    assert call.skip_reason == "opted_out"


@pytest.mark.django_db
def test_dograh_webhook_sends_handoff_text(ready, monkeypatch):
    user, org, campaign = ready
    sent = {}

    def fake_send(connection, to_e164, body):
        sent["to"] = to_e164
        sent["body"] = body
        return {"messages": [{"id": "wamid.OUT"}]}

    monkeypatch.setattr("apps.calls.handoff.send_text", fake_send)
    from apps.calls.models import Lead

    lead = Lead.objects.create(organisation=org, phone_e164="+919876543210", campaign=campaign, name="Asha")
    call = CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign, status="in_progress")
    call.attempts.create(dograh_run_id="run-9", status="in_progress")

    body = json.dumps(
        {
            "run_id": "run-9",
            "status": "completed",
            "disposition": "handoff_requested",
            "transcript": "Agent: I don't have that.",
            "recording_url": "https://storage.example/rec.wav",
            "initial_context": {"call_request_id": str(call.id)},
        }
    ).encode()
    signature = hmac.new(b"test-dograh-secret", body, hashlib.sha256).hexdigest()
    client = APIClient()
    response = client.post(
        f"/webhooks/dograh/{org.slug}/",
        data=body,
        content_type="application/json",
        HTTP_X_DOGRAH_SIGNATURE=signature,
        HTTP_X_DOGRAH_TOKEN=org.whatsapp_calling.webhook_token,
    )
    assert response.status_code == 200
    call.refresh_from_db()
    assert call.disposition == "handoff_requested"
    assert call.status == "completed"
    assert sent["to"] == "+919876543210"
    assert "follow up" in sent["body"].lower()
    assert call.handoff_alerts.exists()


@pytest.mark.django_db
def test_dograh_webhook_stores_call_log(ready):
    user, org, campaign = ready
    from apps.calls.models import Lead

    lead = Lead.objects.create(organisation=org, phone_e164="+919876543210", campaign=campaign, name="Asha")
    call = CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign, status="in_progress")
    call.attempts.create(dograh_run_id="run-9", status="in_progress")

    body = json.dumps(
        {
            "run_id": "run-9",
            "status": "completed",
            "call_time": "2026-10-02T09:15:00+00:00",
            "duration_seconds": "74",
            "end_reason": "user_hangup",
            "disposition": "interested",
            "initial_context": {"call_request_id": str(call.id)},
        }
    ).encode()
    signature = hmac.new(b"test-dograh-secret", body, hashlib.sha256).hexdigest()
    client = APIClient()
    response = client.post(
        f"/webhooks/dograh/{org.slug}/",
        data=body,
        content_type="application/json",
        HTTP_X_DOGRAH_SIGNATURE=signature,
        HTTP_X_DOGRAH_TOKEN=org.whatsapp_calling.webhook_token,
    )
    assert response.status_code == 200
    attempt = call.attempts.get()
    assert attempt.started_at == datetime(2026, 10, 2, 9, 15, tzinfo=dt_timezone.utc)
    assert attempt.duration_seconds == 74
    assert attempt.ended_by == "caller"
    assert attempt.end_reason == "user_hangup"
    assert attempt.ended_at == datetime(2026, 10, 2, 9, 16, 14, tzinfo=dt_timezone.utc)


@pytest.mark.django_db
def test_dograh_webhook_records_agent_hangup(ready):
    user, org, campaign = ready
    from apps.calls.models import Lead

    lead = Lead.objects.create(organisation=org, phone_e164="+919876543210", campaign=campaign, name="Asha")
    call = CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign, status="in_progress")
    call.attempts.create(dograh_run_id="run-10", status="in_progress")

    body = json.dumps(
        {
            "run_id": "run-10",
            "status": "completed",
            "gathered_context": {"call_status": "end_call", "call_disposition": "completed"},
            "cost_info": {"call_duration_seconds": 30},
            "initial_context": {"call_request_id": str(call.id)},
        }
    ).encode()
    signature = hmac.new(b"test-dograh-secret", body, hashlib.sha256).hexdigest()
    client = APIClient()
    response = client.post(
        f"/webhooks/dograh/{org.slug}/",
        data=body,
        content_type="application/json",
        HTTP_X_DOGRAH_SIGNATURE=signature,
        HTTP_X_DOGRAH_TOKEN=org.whatsapp_calling.webhook_token,
    )
    assert response.status_code == 200
    attempt = call.attempts.get()
    assert attempt.ended_by == "agent"
    assert attempt.end_reason == "end_call"
    assert attempt.duration_seconds == 30


@pytest.mark.django_db
def test_due_calls_dial_inside_window(ready, monkeypatch):
    user, org, campaign = ready
    monkeypatch.setattr(
        "apps.compliance.window.now_ist", lambda: datetime(2026, 9, 28, 9, 5, tzinfo=IST)
    )
    dialed = {}

    def fake_initiate(self, **kwargs):
        dialed["ok"] = True
        return {"run_id": "run-due", "raw": {}}

    monkeypatch.setattr("apps.calls.dograh.DograhClient.initiate_call", fake_initiate)
    from apps.calls.models import Lead

    CallPermission.objects.create(organisation=org, phone_e164="+919123456789", is_permanent=True)
    lead = Lead.objects.create(organisation=org, phone_e164="+919123456789", campaign=campaign)
    CallRequest.objects.create(
        organisation=org,
        lead=lead,
        campaign=campaign,
        status="pending_window",
        scheduled_for=timezone.now() - timedelta(minutes=5),
    )
    assert dispatch_due_calls() == 1
    assert dialed.get("ok") is True


@pytest.mark.django_db
def test_test_call_bypasses_calling_window(ready, monkeypatch):
    """Campaign test-calls (is_test=True) must dial even outside 09:00-21:00 IST."""
    user, org, campaign = ready
    night = datetime(2026, 9, 28, 22, 30, tzinfo=IST)
    monkeypatch.setattr("apps.compliance.window.now_ist", lambda: night)
    queued = {}

    def fake_delay(call_id):
        queued["id"] = call_id

    monkeypatch.setattr("apps.calls.tasks.initiate_call.delay", fake_delay)
    from apps.calls.models import Lead
    from apps.calls.services import apply_decision

    CallPermission.objects.create(organisation=org, phone_e164="+919876543210", is_permanent=True)
    lead = Lead.objects.create(organisation=org, phone_e164="+919876543210", campaign=campaign)
    call = CallRequest.objects.create(
        organisation=org, lead=lead, campaign=campaign, is_test=True, status="queued"
    )
    decision = apply_decision(call, moment=night)
    call.refresh_from_db()
    assert decision.action == "dial"
    assert call.status == "queued"
    assert call.skip_reason == ""
    assert queued.get("id") == str(call.id)


@pytest.mark.django_db
def test_production_call_still_waits_outside_window(ready, monkeypatch):
    user, org, campaign = ready
    night = datetime(2026, 9, 28, 22, 30, tzinfo=IST)
    monkeypatch.setattr("apps.compliance.window.now_ist", lambda: night)
    from apps.calls.models import Lead
    from apps.calls.services import apply_decision

    CallPermission.objects.create(organisation=org, phone_e164="+919876543210", is_permanent=True)
    lead = Lead.objects.create(organisation=org, phone_e164="+919876543210", campaign=campaign)
    call = CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign, status="queued")
    decision = apply_decision(call, moment=night)
    call.refresh_from_db()
    assert decision.action == "schedule"
    assert call.status == "pending_window"
    assert call.skip_reason == "outside_calling_window"
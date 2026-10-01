from datetime import timedelta

import pytest
from django.utils import timezone

from apps.calls.models import CallRequest, Lead
from apps.calls.services import apply_decision
from apps.campaigns.models import Campaign
from apps.compliance.checks import permission_request_limited
from apps.compliance.models import CallPermission
from apps.tenants.services import create_organisation
from apps.whatsapp.asterisk import render_endpoint
from apps.whatsapp.processing import handle_permission_reply, send_permission
from apps.whatsapp.models import InboundWhatsAppMessage


def _setup():
    user = create_organisation("Sundaram Loans", "ops@sundaram.test", "supersecret1")
    org = user.organisation
    org.whatsapp.phone_number_id = "123"
    org.whatsapp.access_token = "token"
    org.whatsapp.app_secret = "secret"
    org.whatsapp.save()
    line = org.plivo
    line.auth_id = "MA_TEST"
    line.auth_token = "token"
    line.caller_id = "+919800000000"
    line.dograh_config_id = 7
    line.save()
    campaign = Campaign.objects.create(organisation=org, name="Offer", dograh_workflow_uuid="wf")
    return org, campaign, line


@pytest.mark.django_db
def test_accept_dials_the_mobile_through_plivo(monkeypatch):
    org, campaign, _calling = _setup()
    seen = {}

    def fake(self, **kwargs):
        seen.update(kwargs)
        return {"run_id": "run", "raw": {}}

    monkeypatch.setattr("apps.calls.dograh.DograhClient.initiate_call", fake)
    lead = Lead.objects.create(organisation=org, phone_e164="+919876543210", campaign=campaign)
    call = CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign, status="awaiting_permission")
    message = InboundWhatsAppMessage.objects.create(
        organisation=org,
        wa_message_id="perm-1",
        phone_raw="919876543210",
        raw={
            "kind": "call_permission_reply",
            "from": "919876543210",
            "permission_response": "accept",
            "permission_permanent": False,
            "permission_expires": int((timezone.now() + timedelta(days=6)).timestamp()),
        },
    )
    handle_permission_reply(message)
    call.refresh_from_db()
    assert call.status == "in_progress"
    assert seen["phone_number"] == "+919876543210"
    assert seen["telephony_configuration_id"] == "7"


@pytest.mark.django_db
def test_reject_does_not_dial(monkeypatch):
    org, campaign, _calling = _setup()
    monkeypatch.setattr(
        "apps.calls.dograh.DograhClient.initiate_call",
        lambda self, **kwargs: (_ for _ in ()).throw(AssertionError("dial")),
    )
    lead = Lead.objects.create(organisation=org, phone_e164="+919876543210", campaign=campaign)
    call = CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign, status="awaiting_permission")
    message = InboundWhatsAppMessage.objects.create(
        organisation=org,
        wa_message_id="perm-2",
        raw={"kind": "call_permission_reply", "from": "919876543210", "permission_response": "reject"},
    )
    handle_permission_reply(message)
    call.refresh_from_db()
    assert call.status == "permission_rejected"


@pytest.mark.django_db
def test_expired_permission_does_not_dial():
    org, campaign, _calling = _setup()
    lead = Lead.objects.create(organisation=org, phone_e164="+919876543210", campaign=campaign)
    CallPermission.objects.create(
        organisation=org, phone_e164=lead.phone_e164, expires_at=timezone.now() - timedelta(minutes=1)
    )
    call = CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign, status="awaiting_permission")
    apply_decision(call)
    call.refresh_from_db()
    assert call.status == "permission_expired"


@pytest.mark.django_db
def test_third_permission_request_is_blocked(monkeypatch):
    org, campaign, _calling = _setup()
    monkeypatch.setattr("apps.whatsapp.processing.send_call_permission_request", lambda *args, **kwargs: {})
    lead = Lead.objects.create(organisation=org, phone_e164="+919876543210", campaign=campaign)
    for _ in range(2):
        CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign, status="completed")
    third = CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign, status="awaiting_permission")
    assert permission_request_limited(third) is True
    send_permission(third)
    third.refresh_from_db()
    assert third.skip_reason == "permission_rate_limited"


@pytest.mark.django_db
def test_sixth_call_in_a_day_is_blocked():
    org, campaign, _calling = _setup()
    lead = Lead.objects.create(organisation=org, phone_e164="+919876543210", campaign=campaign)
    CallPermission.objects.create(organisation=org, phone_e164=lead.phone_e164, is_permanent=True)
    for _ in range(5):
        CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign, status="completed")
    sixth = CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign)
    apply_decision(sixth)
    sixth.refresh_from_db()
    assert sixth.skip_reason == "call_rate_limited"


def test_endpoint_has_webrtc_and_does_not_log_password(caplog):
    class Calling:
        sip_password = "super-secret-pass"
        asterisk_endpoint = "wa_sundaram"
        business_number_e164 = "+919800000000"

    text = render_endpoint(Calling())
    assert "webrtc=yes" in text
    assert "919800000000" in text
    assert "super-secret-pass" not in caplog.text

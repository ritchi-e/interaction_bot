import uuid

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.calls.models import CallRequest, Lead
from apps.campaigns.locum_api import LOCUM_CAMPAIGN_ID
from apps.campaigns.locum_source import placeholder_leads, template_vars
from apps.campaigns.models import Campaign, LocumInterest
from apps.tenants.services import create_organisation


def test_placeholder_leads_have_phone_and_job():
    leads = placeholder_leads()
    assert leads
    for lead in leads:
        assert lead["phone_e164"]
        assert lead["job_title"]
        assert "job_title" in template_vars(lead)


@pytest.mark.django_db
def test_internal_interest_saves_phone_job_and_flag(settings):
    settings.INTERNAL_API_TOKEN = "secret"
    user = create_organisation("Locum Org", "ops@locum.test", "supersecret1")
    org = user.organisation
    campaign = Campaign.objects.create(
        id=uuid.UUID(LOCUM_CAMPAIGN_ID),
        organisation=org,
        name="locum",
        language="hi",
        tts_voice="female",
    )
    lead = Lead.objects.create(organisation=org, campaign=campaign, phone_e164="+919876543210", name="Dr A")
    call = CallRequest.objects.create(organisation=org, lead=lead, campaign=campaign, status="in_progress")
    LocumInterest.objects.create(
        organisation=org,
        campaign=campaign,
        call_request=call,
        phone_e164=lead.phone_e164,
        doctor_name="Dr A",
        job_id="job-1",
        job_title="Emergency duty",
        job_location="Mumbai",
    )
    client = APIClient()
    response = client.post(
        "/internal/locum/interest/",
        {"campaign_id": str(campaign.id), "call_request_id": str(call.id), "interested": "yes"},
        format="json",
        HTTP_X_INTERNAL_TOKEN="secret",
    )
    assert response.status_code == 200
    row = LocumInterest.objects.get(call_request=call)
    assert row.interested == "yes"
    assert row.phone_e164 == "+919876543210"
    assert row.job_title == "Emergency duty"
    call.refresh_from_db()
    assert call.disposition == "interested"


@pytest.mark.django_db
def test_locum_interest_list():
    user = create_organisation("Locum Org", "ops@locum.test", "supersecret1")
    org = user.organisation
    campaign = Campaign.objects.create(
        id=uuid.UUID(LOCUM_CAMPAIGN_ID),
        organisation=org,
        name="locum",
        language="hi",
        tts_voice="female",
    )
    LocumInterest.objects.create(
        organisation=org,
        campaign=campaign,
        phone_e164="+919811122233",
        job_title="OPD cover",
        interested="no",
    )
    client = APIClient()
    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    response = client.get("/api/locum-interests/")
    assert response.status_code == 200
    payload = response.json()
    rows = payload if isinstance(payload, list) else payload["results"]
    assert len(rows) == 1
    assert rows[0]["interested"] == "no"
    assert rows[0]["job_title"] == "OPD cover"

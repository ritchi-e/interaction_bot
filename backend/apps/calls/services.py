from datetime import timedelta

from django.utils import timezone

import httpx

from apps.agents.model_overrides import tts_prewarm_target
from apps.calls.dograh import DograhClient, DograhError
from apps.calls.models import CallRequest
from apps.campaigns.models import Campaign
from apps.compliance.checks import evaluate_call
from apps.compliance.phones import digits_only, normalise_indian_mobile
from apps.tenants.models import PlivoLine


def _prewarm_greeting(campaign, keys, text):
    """Ask speech-tts to start synthesizing the greeting right away.

    Fired just before we dial, so the voice is already rendered by the time
    Plivo finishes ringing and Dograh actually asks for it (see
    speech/tts/server.py's /v1/audio/prewarm). Best-effort only: any failure
    here just means the call falls back to the normal on-demand path.
    """

    text = (text or "").strip()
    if not text:
        return
    target = tts_prewarm_target(campaign, keys)
    if not target:
        return
    base_url, model = target
    from django.conf import settings

    token = (settings.SPEECH_API_TOKEN or "local").strip() or "local"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        httpx.post(
            f"{base_url}/audio/prewarm",
            json={"input": text, "model": model},
            headers=headers,
            timeout=2.0,
        )
    except httpx.HTTPError:
        pass


def _same_number(left, right):
    left_digits = digits_only(left)
    right_digits = digits_only(right)
    if not left_digits or not right_digits:
        return False
    return left_digits == right_digits or left_digits[-10:] == right_digits[-10:]


def _caller_phone(raw):
    mobile = normalise_indian_mobile(raw)
    if mobile:
        return mobile
    digits = digits_only(raw)
    if not digits:
        return ""
    return "+" + digits[:19]


def open_inbound_call(*, caller_number, called_number, provider_call_id=""):
    """Start, or continue, the campaign bound to the number that was dialed.

    An inbound Dograh run does not carry a campaign. The guard asks for one
    on the first turn, and again on later turns of the same phone call.
    """

    caller = _caller_phone(caller_number)
    if not caller:
        return None
    line = next(
        (
            item
            for item in PlivoLine.objects.select_related("organisation")
            if item.inbound_campaign_id and _same_number(item.caller_id, called_number)
        ),
        None,
    )
    if line is None:
        return None
    campaign = Campaign.objects.filter(pk=line.inbound_campaign_id, organisation=line.organisation, is_active=True).first()
    if campaign is None:
        return None
    from apps.calls.models import Lead

    lead, _created = Lead.objects.get_or_create(
        organisation=line.organisation,
        phone_e164=caller,
        defaults={"campaign": campaign},
    )
    marker = f"inbound:{(provider_call_id or '').strip()}" if (provider_call_id or "").strip() else ""
    existing = None
    if marker:
        existing = CallRequest.objects.filter(campaign=campaign, source_message_id=marker).order_by("-created_at").first()
    if existing is None and not marker:
        existing = (
            CallRequest.objects.filter(
                campaign=campaign,
                lead=lead,
                status="in_progress",
                created_at__gte=timezone.now() - timedelta(minutes=30),
            )
            .order_by("-created_at")
            .first()
        )
    if existing is None:
        existing = CallRequest.objects.create(
            organisation=line.organisation,
            lead=lead,
            campaign=campaign,
            status="in_progress",
            source_message_id=marker,
        )
        existing.attempts.create(status="in_progress", started_at=timezone.now())
    return {
        "campaign_id": str(campaign.id),
        "call_request_id": str(existing.id),
        "language": campaign.language,
        "campaign_name": campaign.name,
    }


def apply_decision(call_request, moment=None, *, sync=False):
    decision = evaluate_call(call_request, moment=moment)
    if decision.action == "dial":
        call_request.status = "queued"
        call_request.skip_reason = ""
        call_request.scheduled_for = None
        call_request.save(update_fields=["status", "skip_reason", "scheduled_for", "updated_at"])
        if sync:
            place_dograh_call(call_request)
        else:
            from apps.calls.tasks import initiate_call

            initiate_call.delay(str(call_request.id))
        return decision
    if decision.action == "schedule":
        call_request.status = "pending_window"
        call_request.skip_reason = decision.reason
        call_request.scheduled_for = decision.scheduled_for
        call_request.save(update_fields=["status", "skip_reason", "scheduled_for", "updated_at"])
        return decision
    call_request.status = "skipped"
    call_request.skip_reason = decision.reason
    if decision.reason == "permission_expired":
        call_request.status = "permission_expired"
    call_request.save(update_fields=["status", "skip_reason", "updated_at"])
    return decision


def place_dograh_call(call_request):
    decision = evaluate_call(call_request)
    if decision.action != "dial":
        apply_decision(call_request)
        return None

    campaign = call_request.campaign
    lead = call_request.lead
    plivo = getattr(call_request.organisation, "plivo", None)
    keys = getattr(call_request.organisation, "provider_keys", None)
    api_key = keys.dograh_api_key if keys and keys.dograh_api_key else ""
    agent = getattr(campaign, "agent_profile", None)
    workflow_uuid = (agent.dograh_workflow_uuid if agent and agent.dograh_workflow_uuid else "") or campaign.dograh_workflow_uuid

    if agent is not None:
        _prewarm_greeting(campaign, keys, agent.greeting)

    initial_context = {
        "campaign_id": str(campaign.id),
        "call_request_id": str(call_request.id),
        "customer_name": lead.name or "there",
        "language": campaign.language,
        "campaign_name": campaign.name,
        "caller_id": decision.caller_id,
    }
    client = DograhClient(api_key=api_key or None)
    call_request.status = "dialing"
    call_request.save(update_fields=["status", "updated_at"])
    attempt = call_request.attempts.create(status="dialing", started_at=timezone.now())
    try:
        result = client.initiate_call(
            phone_number=lead.phone_e164,
            initial_context=initial_context,
            workflow_uuid=workflow_uuid,
            trigger_uuid=campaign.dograh_trigger_uuid,
            telephony_configuration_id=str(plivo.dograh_config_id) if plivo and plivo.dograh_config_id else "",
        )
    except (DograhError, httpx.HTTPError) as exc:
        attempt.status = "failed"
        attempt.error = str(exc)
        attempt.ended_at = timezone.now()
        attempt.save(update_fields=["status", "error", "ended_at", "updated_at"])
        call_request.status = "failed"
        call_request.skip_reason = "dograh_error"
        call_request.save(update_fields=["status", "skip_reason", "updated_at"])
        retryable = isinstance(exc, httpx.HTTPError) or (isinstance(exc, DograhError) and (exc.status_code or 0) >= 500)
        if retryable:
            raise
        return None

    attempt.dograh_run_id = result["run_id"]
    attempt.save(update_fields=["dograh_run_id", "updated_at"])
    call_request.status = "in_progress"
    call_request.save(update_fields=["status", "updated_at"])
    return attempt

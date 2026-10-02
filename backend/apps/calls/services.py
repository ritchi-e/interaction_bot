from django.utils import timezone

import httpx

from apps.agents.model_overrides import rumik_bridge_target
from apps.calls.dograh import DograhClient, DograhError
from apps.compliance.checks import evaluate_call


def _prewarm_greeting(campaign, keys, text):
    """Ask the Rumik bridge to start synthesizing the greeting right away.

    Fired just before we dial, so the voice is already rendered by the time
    Plivo finishes ringing and Dograh actually asks for it (see
    context_guard/rumik_bridge.py's /v1/audio/prewarm). Best-effort only: any
    failure here just means the call falls back to the normal on-demand path,
    with no change in behaviour.
    """

    text = (text or "").strip()
    if not text:
        return
    target = rumik_bridge_target(campaign, keys)
    if not target:
        return
    base_url, model = target
    try:
        httpx.post(f"{base_url}/audio/prewarm", json={"input": text, "model": model}, timeout=2.0)
    except httpx.HTTPError:
        pass


def apply_decision(call_request, moment=None):
    decision = evaluate_call(call_request, moment=moment)
    if decision.action == "dial":
        call_request.status = "queued"
        call_request.skip_reason = ""
        call_request.scheduled_for = None
        call_request.save(update_fields=["status", "skip_reason", "scheduled_for", "updated_at"])
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

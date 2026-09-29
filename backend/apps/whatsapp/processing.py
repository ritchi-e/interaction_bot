import logging
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone

from apps.calls.models import CallRequest, Lead
from apps.calls.services import apply_decision
from apps.compliance.checks import permission_request_limited
from apps.compliance.models import CallPermission, OptOut
from apps.compliance.phones import normalise_indian_mobile
from apps.whatsapp.calling import send_call_permission_request
from apps.whatsapp.intents import is_opt_out
from apps.whatsapp.matching import match_campaign

logger = logging.getLogger(__name__)


def process_inbound(message):
    if message.processed_at:
        return
    payload = message.raw or {}
    if payload.get("kind") == "call_permission_reply":
        handle_permission_reply(message)
        return
    organisation = message.organisation
    phone = normalise_indian_mobile(payload.get("from") or message.phone_raw)
    body = payload.get("body") or message.body or ""

    if phone is None:
        message.processing_status = "invalid_phone"
        message.processed_at = timezone.now()
        message.save(update_fields=["processing_status", "processed_at", "updated_at"])
        return

    if is_opt_out(body):
        OptOut.objects.get_or_create(organisation=organisation, phone_e164=phone, defaults={"reason": "whatsapp_stop"})
        message.processing_status = "opted_out"
        message.processed_at = timezone.now()
        message.save(update_fields=["processing_status", "processed_at", "updated_at"])
        return

    campaign, how = match_campaign(
        organisation,
        context_id=payload.get("context_id") or "",
        button_payload=payload.get("button_payload") or "",
        body=body,
    )
    if campaign is None:
        message.processing_status = "unmatched"
        message.processed_at = timezone.now()
        message.save(update_fields=["processing_status", "processed_at", "updated_at"])
        return

    lead, _created = Lead.objects.get_or_create(
        organisation=organisation,
        phone_e164=phone,
        defaults={"name": payload.get("contact_name") or "", "campaign": campaign, "wa_message_id": message.wa_message_id},
    )
    if payload.get("contact_name") and not lead.name:
        lead.name = payload["contact_name"]
    lead.campaign = campaign
    lead.wa_message_id = message.wa_message_id
    lead.save(update_fields=["name", "campaign", "wa_message_id", "updated_at"])

    call_request = lead.call_requests.create(
        organisation=organisation,
        campaign=campaign,
        source_message_id=message.wa_message_id,
        status="awaiting_permission",
        is_test=bool(payload.get("is_test")),
    )
    send_permission(call_request)
    message.matched_campaign_id = campaign.id
    message.processing_status = f"call_{call_request.status}:{how}"
    message.processed_at = timezone.now()
    message.save(update_fields=["matched_campaign_id", "processing_status", "processed_at", "updated_at"])
    logger.info("whatsapp %s -> campaign %s via %s", message.wa_message_id, campaign.id, how)


def send_permission(call_request):
    if permission_request_limited(call_request):
        call_request.status = "skipped"
        call_request.skip_reason = "permission_rate_limited"
        call_request.save(update_fields=["status", "skip_reason", "updated_at"])
        return
    organisation = call_request.organisation
    connection = getattr(organisation, "whatsapp", None)
    calling = getattr(organisation, "whatsapp_calling", None)
    text = (call_request.campaign.permission_message or "").strip()
    if not text and calling:
        text = calling.permission_message
    if connection is None or not connection.is_configured:
        call_request.status = "failed"
        call_request.skip_reason = "whatsapp_not_configured"
        call_request.save(update_fields=["status", "skip_reason", "updated_at"])
        return
    send_call_permission_request(connection, call_request.lead.phone_e164, text or "May we call you?")
    call_request.status = "awaiting_permission"
    call_request.save(update_fields=["status", "updated_at"])


def handle_permission_reply(message):
    organisation = message.organisation
    payload = message.raw or {}
    phone = normalise_indian_mobile(payload.get("from") or message.phone_raw)
    if phone is None:
        message.processing_status = "invalid_phone"
        message.processed_at = timezone.now()
        message.save(update_fields=["processing_status", "processed_at", "updated_at"])
        return
    call_request = (
        CallRequest.objects.filter(
            organisation=organisation, lead__phone_e164=phone, status="awaiting_permission"
        )
        .order_by("-created_at")
        .first()
    )
    response = payload.get("permission_response")
    if response == "accept" and call_request:
        expires = payload.get("permission_expires")
        expires_at = None
        if expires:
            expires_at = datetime.fromtimestamp(int(expires), tz=dt_timezone.utc)
        CallPermission.objects.create(
            organisation=organisation,
            phone_e164=phone,
            is_permanent=bool(payload.get("permission_permanent")),
            expires_at=expires_at,
        )
        apply_decision(call_request)
    elif response == "reject" and call_request:
        call_request.status = "permission_rejected"
        call_request.skip_reason = "permission_rejected"
        call_request.save(update_fields=["status", "skip_reason", "updated_at"])
    message.processing_status = f"permission_{response or 'unknown'}"
    message.processed_at = timezone.now()
    message.save(update_fields=["processing_status", "processed_at", "updated_at"])

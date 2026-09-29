import logging

from django.utils import timezone

from apps.calls.models import HandoffAlert
from apps.whatsapp.client import send_text

logger = logging.getLogger(__name__)

FOLLOW_UP = "Thanks for your time. A teammate will follow up with you shortly on this chat."


def notify_handoff(call_request):
    if HandoffAlert.objects.filter(call_request=call_request).exists():
        return
    context = getattr(call_request.campaign, "context", None)
    detail = context.handoff_message if context else FOLLOW_UP
    alert = HandoffAlert.objects.create(
        organisation=call_request.organisation,
        call_request=call_request,
        message=f"{call_request.lead.phone_e164}: {detail}",
    )
    whatsapp = getattr(call_request.organisation, "whatsapp", None)
    if whatsapp and whatsapp.is_configured:
        try:
            send_text(whatsapp, call_request.lead.phone_e164, FOLLOW_UP)
            alert.whatsapp_sent_at = timezone.now()
            alert.save(update_fields=["whatsapp_sent_at"])
        except Exception:
            logger.exception("WhatsApp handoff text failed for call %s", call_request.id)
    call_request.disposition = "handoff_requested"
    call_request.save(update_fields=["disposition", "updated_at"])

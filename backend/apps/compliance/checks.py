from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.compliance.models import CallPermission, OptOut
from apps.compliance.phones import normalise_indian_mobile
from apps.compliance.window import calling_window

BLOCKING_STATUSES = ("queued", "dialing", "in_progress", "completed", "pending_window")
CALL_STATUSES = BLOCKING_STATUSES


def has_valid_permission(organisation, phone, moment=None):
    permission = (
        CallPermission.objects.filter(organisation=organisation, phone_e164=phone).order_by("-created_at").first()
    )
    if permission is None:
        return False
    if permission.is_permanent:
        return True
    if permission.expires_at is None:
        return False
    now = moment or timezone.now()
    return permission.expires_at > now


def permission_request_limited(call_request):
    since = timezone.now() - timedelta(days=7)
    count = (
        call_request.organisation.call_requests.filter(
            lead__phone_e164=call_request.lead.phone_e164,
            created_at__gte=since,
        )
        .exclude(pk=call_request.pk)
        .exclude(is_test=True)
        .count()
    )
    return count >= 2


def calls_per_day_limited(call_request):
    if call_request.is_test:
        return False
    since = timezone.now() - timedelta(hours=24)
    count = call_request.lead.call_requests.filter(created_at__gte=since, status__in=CALL_STATUSES).exclude(
        pk=call_request.pk
    ).exclude(is_test=True).count()
    return count >= 5


@dataclass
class Decision:
    action: str
    reason: str = ""
    scheduled_for: object = None
    caller_id: str = ""


def is_rate_limited(call_request):
    if call_request.is_test:
        return False
    since = timezone.now() - timedelta(hours=settings.MAX_CALLS_PER_LEAD_CAMPAIGN_HOURS)
    return (
        call_request.lead.call_requests.filter(
            campaign=call_request.campaign,
            created_at__gte=since,
            status__in=BLOCKING_STATUSES,
        )
        .exclude(pk=call_request.pk)
        .exclude(is_test=True)
        .exists()
    )


def evaluate_call(call_request, moment=None):
    phone = normalise_indian_mobile(call_request.lead.phone_e164)
    if phone is None:
        return Decision("reject", "not_an_indian_mobile")

    if OptOut.objects.filter(organisation=call_request.organisation, phone_e164=phone).exists():
        return Decision("reject", "opted_out")

    if calls_per_day_limited(call_request):
        return Decision("reject", "call_rate_limited")

    if is_rate_limited(call_request):
        return Decision("reject", "rate_limited")

    if not has_valid_permission(call_request.organisation, phone):
        latest = (
            CallPermission.objects.filter(organisation=call_request.organisation, phone_e164=phone)
            .order_by("-created_at")
            .first()
        )
        if latest and not latest.is_permanent:
            return Decision("reject", "permission_expired")
        return Decision("reject", "no_permission")

    calling = getattr(call_request.organisation, "whatsapp_calling", None)
    if calling is None or not calling.is_ready:
        return Decision("reject", "whatsapp_calling_not_ready")

    allowed, next_at = calling_window(moment)
    if not allowed:
        return Decision("schedule", "outside_calling_window", scheduled_for=next_at)

    return Decision("dial", caller_id=calling.business_number_e164)

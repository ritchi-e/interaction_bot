import logging

import httpx
from celery import shared_task

from apps.calls.dograh import DograhError
from django.utils import timezone

from apps.calls.models import CallRequest
from apps.calls.services import place_dograh_call
from apps.compliance.window import calling_window, now_ist

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(httpx.HTTPError, DograhError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def initiate_call(self, call_request_id):
    call_request = CallRequest.objects.select_related(
        "lead", "campaign", "organisation", "organisation__whatsapp_calling", "organisation__provider_keys"
    ).get(pk=call_request_id)
    if call_request.status in ("completed", "skipped", "in_progress"):
        return
    place_dograh_call(call_request)


@shared_task
def dispatch_due_calls():
    moment = now_ist()
    allowed, _next = calling_window(moment)
    if not allowed:
        return 0
    due = CallRequest.objects.filter(status="pending_window", scheduled_for__lte=timezone.now()).order_by(
        "scheduled_for"
    )
    count = 0
    for call_request in due.iterator():
        initiate_call.delay(str(call_request.id))
        count += 1
    return count

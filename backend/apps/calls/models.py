import uuid

from django.db import models

from apps.campaigns.models import Campaign
from apps.common.models import TimeStampedModel
from apps.tenants.models import Organisation


class Lead(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="leads")
    campaign = models.ForeignKey(Campaign, null=True, blank=True, on_delete=models.SET_NULL, related_name="leads")
    phone_e164 = models.CharField(max_length=20)
    name = models.CharField(max_length=200, blank=True)
    wa_message_id = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("organisation", "phone_e164")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name or self.phone_e164}"


class CallRequest(TimeStampedModel):
    STATUS_CHOICES = [
        ("awaiting_permission", "Awaiting WhatsApp permission"),
        ("permission_rejected", "Permission rejected"),
        ("permission_expired", "Permission expired"),
        ("pending_window", "Waiting for calling window"),
        ("queued", "Queued"),
        ("dialing", "Dialing"),
        ("in_progress", "In progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="call_requests")
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="call_requests")
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="call_requests")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="queued")
    skip_reason = models.CharField(max_length=80, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    disposition = models.CharField(max_length=64, blank=True)
    is_test = models.BooleanField(default=False)
    source_message_id = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]


class CallAttempt(TimeStampedModel):
    call_request = models.ForeignKey(CallRequest, on_delete=models.CASCADE, related_name="attempts")
    dograh_run_id = models.CharField(max_length=128, blank=True, db_index=True)
    status = models.CharField(max_length=32, default="dialing")
    transcript = models.TextField(blank=True)
    recording_url = models.CharField(max_length=500, blank=True)
    error = models.TextField(blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)


class HandoffAlert(TimeStampedModel):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="handoff_alerts")
    call_request = models.ForeignKey(CallRequest, on_delete=models.CASCADE, related_name="handoff_alerts")
    message = models.TextField()
    whatsapp_sent_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ContextViolation(TimeStampedModel):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="violations")
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="violations")
    call_request = models.ForeignKey(
        CallRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name="violations"
    )
    sentence = models.TextField()
    reason = models.CharField(max_length=80)

    class Meta:
        ordering = ["-created_at"]

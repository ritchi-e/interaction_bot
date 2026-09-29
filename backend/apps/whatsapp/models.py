from django.db import models

from apps.common.models import TimeStampedModel
from apps.tenants.models import Organisation


class InboundWhatsAppMessage(TimeStampedModel):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="inbound_messages")
    wa_message_id = models.CharField(max_length=255, unique=True)
    phone_raw = models.CharField(max_length=32, blank=True)
    body = models.TextField(blank=True)
    raw = models.JSONField(default=dict)
    matched_campaign_id = models.UUIDField(null=True, blank=True)
    processing_status = models.CharField(max_length=32, default="received")
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

from django.db import models

from apps.campaigns.models import Campaign
from apps.common.models import TimeStampedModel


class AgentProfile(TimeStampedModel):
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name="agent_profile")
    role = models.CharField(max_length=120, blank=True, default="customer advisor")
    persona = models.TextField(blank=True)
    greeting = models.TextField(blank=True, default="Hello, this is a call about the message you replied to.")
    closing_line = models.TextField(blank=True, default="Thank you for your time. Goodbye.")
    allow_interrupt = models.BooleanField(default=True)
    max_call_seconds = models.PositiveIntegerField(default=300)
    dograh_workflow_id = models.PositiveIntegerField(null=True, blank=True)
    dograh_workflow_uuid = models.CharField(max_length=64, blank=True)
    last_published_at = models.DateTimeField(null=True, blank=True)
    publish_error = models.TextField(blank=True)

    def __str__(self):
        return f"Agent for {self.campaign_id}"

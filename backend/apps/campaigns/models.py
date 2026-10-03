import uuid

from django.db import models

from apps.common.models import TimeStampedModel
from apps.tenants.models import Organisation


class Campaign(TimeStampedModel):
    LANGUAGE_CHOICES = [
        ("hi", "Hindi"),
        ("en_in", "Indian English"),
    ]
    # Self-hosted system voices: Indian-accent female / male. Language comes
    # from ``language``; Hindi already includes English loanwords in speech.
    VOICE_CHOICES = [
        ("female", "Female"),
        ("male", "Male"),
    ]
    TTS_CHOICES = [
        ("", "Organisation default"),
        ("sarvam", "Sarvam Bulbul"),
        ("rumik", "Rumik"),
        ("cartesia", "Cartesia"),
        ("elevenlabs", "ElevenLabs"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=200)
    language = models.CharField(max_length=16, choices=LANGUAGE_CHOICES, default="hi")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    dograh_workflow_uuid = models.CharField(max_length=64, blank=True)
    dograh_trigger_uuid = models.CharField(max_length=64, blank=True)
    permission_message = models.CharField(max_length=500, blank=True)
    tts_provider = models.CharField(max_length=32, choices=TTS_CHOICES, blank=True, default="")
    tts_voice = models.CharField(max_length=80, choices=VOICE_CHOICES, blank=True, default="female")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            Campaign.objects.filter(organisation=self.organisation, is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )


class CampaignContext(TimeStampedModel):
    """Structured facts the agent is allowed to say. Free-form 'say whatever' is not a field."""

    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name="context")
    agent_name = models.CharField(max_length=80, default="Priya")
    goal = models.TextField(blank=True)
    offer_details = models.TextField(blank=True)
    prices = models.JSONField(default=list, blank=True)
    faqs = models.JSONField(default=list, blank=True)
    allowed_topics = models.JSONField(default=list, blank=True)
    forbidden_topics = models.JSONField(default=list, blank=True)
    competitors = models.JSONField(default=list, blank=True)
    handoff_message = models.TextField(
        default="I don't have that information. A teammate will message you on WhatsApp or call you back."
    )

    def price_lines(self):
        lines = []
        for item in self.prices or []:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip()
            amount = str(item.get("amount", "")).strip()
            if label and amount:
                lines.append(f"{label}: Rs {amount}")
        return lines

    def faq_lines(self):
        lines = []
        for item in self.faqs or []:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            if question and answer:
                lines.append(f"Q: {question}\nA: {answer}")
        return lines


class CampaignKeyword(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="keywords")
    keyword = models.CharField(max_length=80)

    class Meta:
        unique_together = [("campaign", "keyword")]


class OutboundTemplateMessage(TimeStampedModel):
    """A WhatsApp message we (or the business sender) sent. Replies quote this id."""

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="outbound_messages")
    wa_message_id = models.CharField(max_length=255, unique=True)
    phone_e164 = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["-created_at"]

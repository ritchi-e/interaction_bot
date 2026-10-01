import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from apps.common.fields import EncryptedTextField
from apps.common.models import TimeStampedModel


class Organisation(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    objects = UserManager()
    organisation = models.ForeignKey(
        Organisation,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="users",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class BusinessProfile(TimeStampedModel):
    organisation = models.OneToOneField(Organisation, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    industry = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.display_name or self.organisation.name


class WhatsAppConnection(TimeStampedModel):
    organisation = models.OneToOneField(
        Organisation, on_delete=models.CASCADE, related_name="whatsapp"
    )
    waba_id = models.CharField(max_length=64, blank=True)
    phone_number_id = models.CharField(max_length=64, blank=True)
    access_token = EncryptedTextField(blank=True)
    app_secret = EncryptedTextField(blank=True)
    verify_token = models.CharField(max_length=128)

    @property
    def is_configured(self):
        return bool(self.phone_number_id and self.access_token and self.app_secret and self.verify_token)


class WhatsAppCalling(TimeStampedModel):
    """WhatsApp Cloud calling for this business. Meta issues the SIP password."""

    organisation = models.OneToOneField(
        Organisation, on_delete=models.CASCADE, related_name="whatsapp_calling"
    )
    business_number_e164 = models.CharField(max_length=20, blank=True)
    calling_enabled = models.BooleanField(default=False)
    sip_enabled = models.BooleanField(default=False)
    sip_password = EncryptedTextField(blank=True)
    asterisk_endpoint = models.CharField(max_length=40, blank=True)
    webhook_token = models.CharField(max_length=80, blank=True)
    permission_message = models.CharField(
        max_length=500,
        default="May we call you on WhatsApp about the message you replied to?",
    )

    @property
    def is_ready(self):
        return bool(self.calling_enabled and self.sip_enabled and self.sip_password and self.asterisk_endpoint)


class PlivoLine(TimeStampedModel):
    """The phone line Dograh uses to dial this business's customers.

    A WhatsApp reply still starts the campaign. The call itself is a normal
    phone call placed through Plivo, not a WhatsApp call.
    """

    organisation = models.OneToOneField(
        Organisation, on_delete=models.CASCADE, related_name="plivo"
    )
    auth_id = models.CharField(max_length=64, blank=True)
    auth_token = EncryptedTextField(blank=True)
    caller_id = models.CharField(max_length=20, blank=True)
    dograh_config_id = models.PositiveIntegerField(null=True, blank=True)
    dograh_phone_number_id = models.PositiveIntegerField(null=True, blank=True)

    @property
    def is_ready(self):
        return bool(self.auth_id and self.auth_token and self.caller_id and self.dograh_config_id)


class ProviderKeys(TimeStampedModel):
    TTS_CHOICES = [
        ("sarvam", "Sarvam Bulbul"),
        ("rumik", "Rumik"),
        ("cartesia", "Cartesia"),
        ("elevenlabs", "ElevenLabs"),
    ]

    organisation = models.OneToOneField(
        Organisation, on_delete=models.CASCADE, related_name="provider_keys"
    )
    deepgram_api_key = EncryptedTextField(blank=True)
    tts_provider = models.CharField(max_length=32, choices=TTS_CHOICES, default="sarvam")
    tts_voice = models.CharField(max_length=80, blank=True, default="anushka")
    sarvam_api_key = EncryptedTextField(blank=True)
    rumik_api_key = EncryptedTextField(blank=True)
    cartesia_api_key = EncryptedTextField(blank=True)
    elevenlabs_api_key = EncryptedTextField(blank=True)
    dograh_api_key = EncryptedTextField(blank=True)

    def key_for(self, provider):
        return {
            "sarvam": self.sarvam_api_key,
            "rumik": self.rumik_api_key,
            "cartesia": self.cartesia_api_key,
            "elevenlabs": self.elevenlabs_api_key,
        }.get(provider, "")

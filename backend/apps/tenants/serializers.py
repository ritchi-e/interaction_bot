from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.tenants.models import (
    BusinessProfile,
    Organisation,
    PlivoLine,
    ProviderKeys,
    User,
    WhatsAppCalling,
    WhatsAppConnection,
)


def mask(value):
    if not value:
        return ""
    tail = value[-4:] if len(value) > 4 else ""
    return f"••••{tail}"


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    organisation_name = serializers.CharField(max_length=200)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate_password(self, value):
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source="organisation.name", read_only=True)
    organisation_slug = serializers.CharField(source="organisation.slug", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "organisation", "organisation_name", "organisation_slug"]


class BusinessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = ["display_name", "description", "industry"]


class WhatsAppConnectionSerializer(serializers.ModelSerializer):
    access_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    app_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    access_token_masked = serializers.SerializerMethodField()
    app_secret_masked = serializers.SerializerMethodField()

    class Meta:
        model = WhatsAppConnection
        fields = [
            "waba_id",
            "phone_number_id",
            "verify_token",
            "access_token",
            "app_secret",
            "access_token_masked",
            "app_secret_masked",
            "is_configured",
        ]
        read_only_fields = ["is_configured"]

    def get_access_token_masked(self, obj):
        return mask(obj.access_token)

    def get_app_secret_masked(self, obj):
        return mask(obj.app_secret)

    def update(self, instance, validated_data):
        for secret in ("access_token", "app_secret"):
            if secret in validated_data and validated_data[secret] == "":
                validated_data.pop(secret)
        return super().update(instance, validated_data)


class WhatsAppCallingSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppCalling
        fields = [
            "business_number_e164",
            "calling_enabled",
            "sip_enabled",
            "asterisk_endpoint",
            "permission_message",
            "is_ready",
        ]
        read_only_fields = ["calling_enabled", "sip_enabled", "asterisk_endpoint", "is_ready"]


class PlivoLineSerializer(serializers.ModelSerializer):
    auth_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    auth_token_masked = serializers.SerializerMethodField()

    class Meta:
        model = PlivoLine
        fields = [
            "auth_id",
            "auth_token",
            "auth_token_masked",
            "caller_id",
            "dograh_config_id",
            "is_ready",
        ]
        read_only_fields = ["dograh_config_id", "is_ready"]

    def get_auth_token_masked(self, obj):
        return mask(obj.auth_token)

    def update(self, instance, validated_data):
        if validated_data.get("auth_token", None) == "":
            validated_data.pop("auth_token")
        return super().update(instance, validated_data)


class ProviderKeysSerializer(serializers.ModelSerializer):
    deepgram_api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    sarvam_api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    rumik_api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    cartesia_api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    elevenlabs_api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    dograh_api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    deepgram_configured = serializers.SerializerMethodField()
    tts_key_configured = serializers.SerializerMethodField()

    class Meta:
        model = ProviderKeys
        fields = [
            "tts_provider",
            "tts_voice",
            "deepgram_api_key",
            "sarvam_api_key",
            "rumik_api_key",
            "cartesia_api_key",
            "elevenlabs_api_key",
            "dograh_api_key",
            "deepgram_configured",
            "tts_key_configured",
        ]

    def get_deepgram_configured(self, obj):
        return bool(obj.deepgram_api_key)

    def get_tts_key_configured(self, obj):
        return bool(obj.key_for(obj.tts_provider))

    def update(self, instance, validated_data):
        for secret in (
            "deepgram_api_key",
            "sarvam_api_key",
            "rumik_api_key",
            "cartesia_api_key",
            "elevenlabs_api_key",
            "dograh_api_key",
        ):
            if secret in validated_data and validated_data[secret] == "":
                validated_data.pop(secret)
        return super().update(instance, validated_data)

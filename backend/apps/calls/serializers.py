from rest_framework import serializers

from apps.calls.models import CallAttempt, CallRequest, ContextViolation, HandoffAlert, Lead


class CallAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallAttempt
        fields = ["id", "dograh_run_id", "status", "transcript", "recording_url", "error", "created_at", "ended_at"]


class ContextViolationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContextViolation
        fields = ["id", "sentence", "reason", "created_at"]


class HandoffAlertSerializer(serializers.ModelSerializer):
    call_request_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = HandoffAlert
        fields = ["id", "call_request_id", "message", "whatsapp_sent_at", "acknowledged_at", "created_at"]


class CallRequestSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    phone_e164 = serializers.CharField(source="lead.phone_e164", read_only=True)
    campaign_name = serializers.CharField(source="campaign.name", read_only=True)
    attempts = CallAttemptSerializer(many=True, read_only=True)
    violations = ContextViolationSerializer(many=True, read_only=True)

    class Meta:
        model = CallRequest
        fields = [
            "id",
            "status",
            "skip_reason",
            "scheduled_for",
            "disposition",
            "is_test",
            "lead_name",
            "phone_e164",
            "campaign",
            "campaign_name",
            "attempts",
            "violations",
            "created_at",
        ]


class LeadSerializer(serializers.ModelSerializer):
    campaign_name = serializers.CharField(source="campaign.name", read_only=True)

    class Meta:
        model = Lead
        fields = ["id", "name", "phone_e164", "campaign", "campaign_name", "wa_message_id", "created_at"]

from rest_framework import serializers

from apps.agents.models import AgentProfile


class AgentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentProfile
        fields = [
            "role",
            "persona",
            "greeting",
            "closing_line",
            "allow_interrupt",
            "max_call_seconds",
            "dograh_workflow_id",
            "dograh_workflow_uuid",
            "last_published_at",
            "publish_error",
        ]
        read_only_fields = [
            "dograh_workflow_id",
            "dograh_workflow_uuid",
            "last_published_at",
            "publish_error",
        ]

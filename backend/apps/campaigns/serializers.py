from rest_framework import serializers

from apps.campaigns.models import Campaign, CampaignContext, CampaignKeyword

CONTEXT_FIELDS = [
    "agent_name",
    "goal",
    "offer_details",
    "prices",
    "faqs",
    "allowed_topics",
    "forbidden_topics",
    "competitors",
    "handoff_message",
]


class PriceSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=120)
    amount = serializers.CharField(max_length=40)


class FAQSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=300)
    answer = serializers.CharField(max_length=600)


class CampaignSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(required=False, allow_blank=True, write_only=True)
    goal = serializers.CharField(required=False, allow_blank=True, write_only=True)
    offer_details = serializers.CharField(required=False, allow_blank=True, write_only=True)
    prices = PriceSerializer(many=True, required=False, write_only=True)
    faqs = FAQSerializer(many=True, required=False, write_only=True)
    allowed_topics = serializers.ListField(
        child=serializers.CharField(max_length=80), required=False, write_only=True
    )
    forbidden_topics = serializers.ListField(
        child=serializers.CharField(max_length=80), required=False, write_only=True
    )
    competitors = serializers.ListField(child=serializers.CharField(max_length=80), required=False, write_only=True)
    handoff_message = serializers.CharField(required=False, allow_blank=True, write_only=True)
    keywords = serializers.ListField(child=serializers.CharField(max_length=80), required=False, write_only=True)

    class Meta:
        model = Campaign
        fields = [
            "id",
            "name",
            "language",
            "is_default",
            "is_active",
            "dograh_workflow_uuid",
            "dograh_trigger_uuid",
            "permission_message",
            "tts_provider",
            "tts_voice",
            "created_at",
            *CONTEXT_FIELDS,
            "keywords",
        ]
        read_only_fields = ["id", "created_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        context = getattr(instance, "context", None)
        for field in CONTEXT_FIELDS:
            if context is None:
                data[field] = [] if field in {"prices", "faqs", "allowed_topics", "forbidden_topics", "competitors"} else ""
            else:
                data[field] = getattr(context, field)
        data["keywords"] = list(instance.keywords.values_list("keyword", flat=True))
        return data

    def _split(self, validated):
        context = {field: validated.pop(field) for field in CONTEXT_FIELDS if field in validated}
        keywords = validated.pop("keywords", None)
        return context, keywords

    def _write_related(self, campaign, context, keywords):
        record, _created = CampaignContext.objects.get_or_create(campaign=campaign)
        for field, value in context.items():
            setattr(record, field, value)
        record.save()
        CampaignContext._meta.get_field("campaign").remote_field.set_cached_value(campaign, record)
        if keywords is not None:
            campaign.keywords.all().delete()
            CampaignKeyword.objects.bulk_create(
                [CampaignKeyword(campaign=campaign, keyword=word.strip()) for word in keywords if word.strip()]
            )

    def create(self, validated_data):
        context, keywords = self._split(validated_data)
        campaign = Campaign.objects.create(organisation=self.context["organisation"], **validated_data)
        self._write_related(campaign, context, keywords if keywords is not None else [])
        return campaign

    def update(self, instance, validated_data):
        context, keywords = self._split(validated_data)
        campaign = super().update(instance, validated_data)
        self._write_related(campaign, context, keywords)
        return campaign

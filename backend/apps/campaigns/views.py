import hmac

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agents.model_overrides import voice_preset_for
from apps.calls.serializers import CallRequestSerializer
from apps.calls.models import CallRequest, ContextViolation, Lead
from apps.calls.services import apply_decision, open_inbound_call
from apps.compliance.models import CallPermission
from apps.campaigns.models import Campaign, OutboundTemplateMessage
from apps.campaigns.prompt_compiler import MINIMAL_DOGRAH_PROMPT, compile_system_prompt, facts_block
from apps.campaigns.serializers import CampaignSerializer
from apps.compliance.phones import normalise_indian_mobile


def require_internal(request):
    expected = settings.INTERNAL_API_TOKEN
    given = request.headers.get("X-Internal-Token", "")
    if not expected or not hmac.compare_digest(given, expected):
        raise PermissionDenied("Invalid internal token")


class CampaignViewSet(viewsets.ModelViewSet):
    serializer_class = CampaignSerializer

    def get_queryset(self):
        organisation = self.request.user.organisation
        if organisation is None:
            return Campaign.objects.none()
        return Campaign.objects.filter(organisation=organisation).select_related("context").prefetch_related("keywords")

    def perform_create(self, serializer):
        serializer.save()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organisation"] = self.request.user.organisation
        return context

    @action(detail=True, methods=["post"], url_path="preview-prompt")
    def preview_prompt(self, request, pk=None):
        campaign = self.get_object()
        if not hasattr(campaign, "context"):
            return Response({"detail": "Campaign has no context yet."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "system_prompt": compile_system_prompt(campaign),
                "dograh_node_prompt": MINIMAL_DOGRAH_PROMPT,
                "note": (
                    "Paste dograh_node_prompt into the Dograh agent node. "
                    "The system_prompt is injected by the context guard and is not editable from the call."
                ),
            }
        )

    @action(detail=True, methods=["post"], url_path="test-call")
    def test_call(self, request, pk=None):
        campaign = self.get_object()
        phone = normalise_indian_mobile(request.data.get("phone") or "")
        if phone is None:
            return Response({"detail": "Enter an Indian mobile number."}, status=status.HTTP_400_BAD_REQUEST)
        agent = getattr(campaign, "agent_profile", None)
        published = campaign.dograh_workflow_uuid or (agent and agent.dograh_workflow_uuid)
        if not published and not campaign.dograh_trigger_uuid:
            return Response(
                {"detail": "Publish the agent before placing a call."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        lead, _created = Lead.objects.get_or_create(
            organisation=campaign.organisation,
            phone_e164=phone,
            defaults={"name": request.data.get("name") or "Test", "campaign": campaign},
        )
        call_request = CallRequest.objects.create(
            organisation=campaign.organisation,
            lead=lead,
            campaign=campaign,
            is_test=True,
            status="queued",
        )
        from apps.campaigns.locum_api import LOCUM_CAMPAIGN_ID, ensure_placeholder_for_call

        if str(campaign.id) == LOCUM_CAMPAIGN_ID:
            ensure_placeholder_for_call(campaign, call_request)
        CallPermission.objects.create(
            organisation=campaign.organisation, phone_e164=phone, is_permanent=True
        )
        apply_decision(call_request)
        call_request.refresh_from_db()
        return Response(CallRequestSerializer(call_request).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="outbound-messages")
    def outbound_messages(self, request, pk=None):
        campaign = self.get_object()
        wa_message_id = (request.data.get("wa_message_id") or "").strip()
        if not wa_message_id:
            return Response({"detail": "wa_message_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        phone = normalise_indian_mobile(request.data.get("phone") or "") or ""
        record, created = OutboundTemplateMessage.objects.get_or_create(
            wa_message_id=wa_message_id,
            defaults={"campaign": campaign, "phone_e164": phone},
        )
        if not created and record.campaign_id != campaign.id:
            return Response({"detail": "That message id is already linked to another campaign."}, status=409)
        return Response(
            {"wa_message_id": record.wa_message_id, "campaign": str(campaign.id), "phone_e164": record.phone_e164},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class InternalCampaignContextView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, campaign_id):
        require_internal(request)
        campaign = (
            Campaign.objects.select_related("organisation", "context", "organisation__profile")
            .filter(pk=campaign_id, is_active=True)
            .first()
        )
        if campaign is None or not hasattr(campaign, "context"):
            return Response({"detail": "unknown campaign"}, status=status.HTTP_404_NOT_FOUND)
        profile = getattr(campaign.organisation, "profile", None)
        business_name = profile.display_name if profile and profile.display_name else campaign.organisation.name
        context = campaign.context
        facts = facts_block(context, business_name)
        prompt = compile_system_prompt(campaign)
        locum_templates = {}
        call_request_id = str(request.query_params.get("call_request_id") or "").strip()
        if call_request_id:
            from apps.campaigns.locum_api import LOCUM_CAMPAIGN_ID, ensure_placeholder_for_call, locum_payload
            from apps.campaigns.models import LocumInterest

            if str(campaign.id) == LOCUM_CAMPAIGN_ID:
                row = LocumInterest.objects.filter(call_request_id=call_request_id).order_by("-created_at").first()
                if row is None:
                    call = CallRequest.objects.filter(pk=call_request_id, campaign=campaign).first()
                    if call is not None:
                        row = ensure_placeholder_for_call(campaign, call)
                if row is not None:
                    payload = locum_payload(row)
                    job_block = f"Job for this call:\n{payload['facts']}"
                    facts = f"{facts}\n\n{job_block}"
                    prompt = prompt.rstrip() + f"\n\n{job_block}\n"
                    locum_templates = payload["templates"]
        return Response(
            {
                "campaign_id": str(campaign.id),
                "prompt": prompt,
                "facts": facts,
                "handoff_message": context.handoff_message,
                "forbidden_topics": context.forbidden_topics or [],
                "competitors": context.competitors or [],
                "voice_model": voice_preset_for(campaign),
                "locum_templates": locum_templates,
            }
        )


class InternalViolationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        require_internal(request)
        campaign = Campaign.objects.filter(pk=request.data.get("campaign_id")).first()
        if campaign is None:
            return Response({"detail": "unknown campaign"}, status=status.HTTP_404_NOT_FOUND)
        call_request = None
        call_request_id = request.data.get("call_request_id") or ""
        if call_request_id:
            call_request = CallRequest.objects.filter(pk=call_request_id, campaign=campaign).first()
        violation = ContextViolation.objects.create(
            organisation=campaign.organisation,
            campaign=campaign,
            call_request=call_request,
            sentence=(request.data.get("sentence") or "")[:2000],
            reason=(request.data.get("reason") or "blocked")[:80],
        )
        return Response({"id": violation.id}, status=status.HTTP_201_CREATED)


class InternalInboundCallView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        require_internal(request)
        opened = open_inbound_call(
            caller_number=request.data.get("caller_number") or "",
            called_number=request.data.get("called_number") or "",
            provider_call_id=request.data.get("provider_call_id") or "",
        )
        if opened is None:
            return Response({"detail": "no inbound campaign for this number"}, status=status.HTTP_404_NOT_FOUND)
        return Response(opened)

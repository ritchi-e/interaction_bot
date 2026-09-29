import hashlib
import hmac
import json

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.calls.handoff import notify_handoff
from apps.calls.models import CallAttempt, CallRequest, HandoffAlert
from apps.calls.serializers import CallRequestSerializer, HandoffAlertSerializer
from apps.calls.status import find_call_request, interpret
from apps.tenants.models import Organisation


def dograh_authorized(request, organisation):
    signature = request.headers.get("X-Dograh-Signature", "")
    token = request.headers.get("X-Dograh-Token", "")
    calling = getattr(organisation, "whatsapp_calling", None)
    expected = (calling.webhook_token if calling else "") or ""
    if expected and token and hmac.compare_digest(token, expected):
        return True
    secret = settings.DOGRAH_WEBHOOK_SECRET
    if secret and signature:
        digest = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, signature)
    return bool(settings.DEBUG and not secret)


class DograhWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, slug):
        organisation = get_object_or_404(Organisation, slug=slug)
        if not dograh_authorized(request, organisation):
            return Response({"detail": "invalid signature"}, status=403)
        try:
            payload = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return Response({"detail": "invalid json"}, status=400)

        parsed = interpret(payload if isinstance(payload, dict) else {})
        call_request = find_call_request(parsed)
        if call_request is None or call_request.organisation_id != organisation.id:
            return Response({"status": "ignored"})

        attempt = None
        if parsed["run_id"]:
            attempt = call_request.attempts.filter(dograh_run_id=parsed["run_id"]).first()
        if attempt is None:
            attempt = call_request.attempts.order_by("-created_at").first()
        if attempt is None:
            attempt = CallAttempt.objects.create(call_request=call_request, dograh_run_id=parsed["run_id"])

        if parsed["transcript"]:
            attempt.transcript = parsed["transcript"]
        if parsed["recording_url"]:
            attempt.recording_url = parsed["recording_url"]
        if parsed["status"]:
            attempt.status = parsed["status"]
            call_request.status = parsed["status"] if parsed["status"] != "dialing" else call_request.status
        if parsed["status"] in ("completed", "failed"):
            attempt.ended_at = timezone.now()
        attempt.save()
        if parsed["disposition"]:
            call_request.disposition = parsed["disposition"]
        call_request.save()
        if parsed["handoff"]:
            notify_handoff(call_request)
        return Response({"status": "ok"})


class CallRequestListView(generics.ListAPIView):
    serializer_class = CallRequestSerializer

    def get_queryset(self):
        qs = CallRequest.objects.filter(organisation=self.request.user.organisation).select_related(
            "lead", "campaign"
        ).prefetch_related("attempts", "violations")
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs


class CallRequestDetailView(generics.RetrieveAPIView):
    serializer_class = CallRequestSerializer

    def get_queryset(self):
        return CallRequest.objects.filter(organisation=self.request.user.organisation).select_related(
            "lead", "campaign"
        ).prefetch_related("attempts", "violations", "handoff_alerts")


class LeadListView(generics.ListAPIView):
    def get_serializer_class(self):
        from apps.calls.serializers import LeadSerializer

        return LeadSerializer

    def get_queryset(self):
        from apps.calls.models import Lead

        return Lead.objects.filter(organisation=self.request.user.organisation).select_related("campaign")


class HandoffAlertListView(generics.ListAPIView):
    serializer_class = HandoffAlertSerializer

    def get_queryset(self):
        return HandoffAlert.objects.filter(
            organisation=self.request.user.organisation, acknowledged_at__isnull=True
        )


class HandoffAlertAckView(APIView):
    def post(self, request, pk):
        alert = get_object_or_404(HandoffAlert, pk=pk, organisation=request.user.organisation)
        alert.acknowledged_at = timezone.now()
        alert.save(update_fields=["acknowledged_at", "updated_at"])
        return Response(HandoffAlertSerializer(alert).data)

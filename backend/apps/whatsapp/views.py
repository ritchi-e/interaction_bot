import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.models import Organisation
from apps.whatsapp.models import InboundWhatsAppMessage
from apps.whatsapp.parsing import iter_messages
from apps.whatsapp.signature import verify_meta_signature
from apps.whatsapp.tasks import process_inbound_message


class WhatsAppWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, slug):
        organisation = get_object_or_404(Organisation, slug=slug)
        connection = getattr(organisation, "whatsapp", None)
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge", "")
        if connection and mode == "subscribe" and token and token == connection.verify_token:
            return HttpResponse(challenge, content_type="text/plain")
        return HttpResponse(status=403)

    def post(self, request, slug):
        organisation = get_object_or_404(Organisation, slug=slug)
        connection = getattr(organisation, "whatsapp", None)
        if connection is None or not verify_meta_signature(
            connection.app_secret, request.body, request.headers.get("X-Hub-Signature-256", "")
        ):
            return Response({"detail": "invalid signature"}, status=403)
        try:
            payload = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return Response({"detail": "invalid json"}, status=400)

        accepted = 0
        for message in iter_messages(payload):
            record, created = InboundWhatsAppMessage.objects.get_or_create(
                wa_message_id=message["wa_message_id"],
                defaults={
                    "organisation": organisation,
                    "phone_raw": message["from"],
                    "body": message["body"],
                    "raw": message,
                },
            )
            if created:
                process_inbound_message.delay(record.pk)
                accepted += 1
        return Response({"status": "ok", "accepted": accepted})

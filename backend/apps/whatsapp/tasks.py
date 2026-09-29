from celery import shared_task

from apps.whatsapp.models import InboundWhatsAppMessage
from apps.whatsapp.processing import process_inbound


@shared_task
def process_inbound_message(message_pk):
    message = InboundWhatsAppMessage.objects.select_related("organisation").get(pk=message_pk)
    process_inbound(message)

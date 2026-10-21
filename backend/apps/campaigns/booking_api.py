"""Save an appointment only after the slot is checked, and list the saved rows."""

import datetime
import uuid

from django.db import IntegrityError, transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.calls.models import CallRequest
from apps.campaigns.models import Appointment, Campaign
from apps.campaigns.serializers import AppointmentSerializer
from apps.campaigns.views import require_internal


def _clock(value):
    text = (value or "").strip()
    for pattern in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.datetime.strptime(text, pattern).time().replace(second=0, microsecond=0)
        except ValueError:
            continue
    return None


class AppointmentListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        organisation = self.request.user.organisation
        if organisation is None:
            return Appointment.objects.none()
        return Appointment.objects.filter(organisation=organisation).select_related("campaign")


class InternalAppointmentView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, appointment_id):
        require_internal(request)
        row = Appointment.objects.filter(pk=appointment_id, status="booked").first()
        if row is None:
            return Response({"detail": "unknown appointment"}, status=status.HTTP_404_NOT_FOUND)
        return Response(_row_payload(row))


class InternalBookAppointmentView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        require_internal(request)
        campaign = Campaign.objects.filter(pk=request.data.get("campaign_id"), is_active=True).first()
        if campaign is None:
            return Response({"detail": "unknown campaign"}, status=status.HTTP_404_NOT_FOUND)
        name = str(request.data.get("caller_name") or "").strip()
        try:
            day = datetime.date.fromisoformat(str(request.data.get("date") or ""))
        except ValueError:
            day = None
        clock = _clock(str(request.data.get("time") or ""))
        if not name or day is None or clock is None:
            return Response({"detail": "name, date, and time are required"}, status=status.HTTP_400_BAD_REQUEST)
        call = None
        call_id = str(request.data.get("call_request_id") or "").strip()
        if call_id:
            try:
                uuid.UUID(call_id)
            except ValueError:
                call_id = ""
        if call_id:
            call = CallRequest.objects.filter(pk=call_id, campaign=campaign).first()
        try:
            with transaction.atomic():
                existing = (
                    Appointment.objects.select_for_update()
                    .filter(campaign=campaign, appointment_date=day, appointment_time=clock, status="booked")
                    .first()
                )
                owned = None
                if call is not None:
                    owned = (
                        Appointment.objects.select_for_update()
                        .filter(call_request=call, status="booked")
                        .first()
                    )
                if existing is not None and (owned is None or existing.id != owned.id):
                    return Response({"available": False}, status=status.HTTP_409_CONFLICT)
                if owned is not None:
                    owned.caller_name = name
                    owned.appointment_date = day
                    owned.appointment_time = clock
                    owned.save(update_fields=["caller_name", "appointment_date", "appointment_time", "updated_at"])
                    return Response(_row_payload(owned))
                row = Appointment.objects.create(
                    organisation=campaign.organisation,
                    campaign=campaign,
                    call_request=call,
                    caller_name=name,
                    appointment_date=day,
                    appointment_time=clock,
                )
        except IntegrityError:
            return Response({"available": False}, status=status.HTTP_409_CONFLICT)
        return Response(_row_payload(row), status=status.HTTP_201_CREATED)


def _row_payload(row):
    return {
        "id": str(row.id),
        "caller_name": row.caller_name,
        "date": row.appointment_date.isoformat(),
        "time": row.appointment_time.strftime("%H:%M"),
        "available": True,
    }

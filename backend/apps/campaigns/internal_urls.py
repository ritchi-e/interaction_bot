from django.urls import path

from apps.campaigns.booking_api import InternalAppointmentView, InternalBookAppointmentView
from apps.campaigns.views import InternalCampaignContextView, InternalInboundCallView, InternalViolationView

urlpatterns = [
    path("campaigns/<uuid:campaign_id>/context/", InternalCampaignContextView.as_view(), name="internal-context"),
    path("appointments/book/", InternalBookAppointmentView.as_view(), name="internal-book"),
    path("appointments/<uuid:appointment_id>/", InternalAppointmentView.as_view(), name="internal-appointment"),
    path("violations/", InternalViolationView.as_view(), name="internal-violation"),
    path("calls/inbound/", InternalInboundCallView.as_view(), name="internal-inbound-call"),
]

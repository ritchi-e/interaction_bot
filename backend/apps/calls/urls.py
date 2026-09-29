from django.urls import path

from apps.calls.views import (
    CallRequestDetailView,
    CallRequestListView,
    HandoffAlertAckView,
    HandoffAlertListView,
    LeadListView,
)

urlpatterns = [
    path("calls/", CallRequestListView.as_view(), name="call-list"),
    path("calls/<uuid:pk>/", CallRequestDetailView.as_view(), name="call-detail"),
    path("leads/", LeadListView.as_view(), name="lead-list"),
    path("handoffs/", HandoffAlertListView.as_view(), name="handoff-list"),
    path("handoffs/<int:pk>/ack/", HandoffAlertAckView.as_view(), name="handoff-ack"),
]

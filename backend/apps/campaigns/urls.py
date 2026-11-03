from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.agents.views import CampaignAgentPublishView, CampaignAgentView
from apps.campaigns.booking_api import AppointmentListView
from apps.campaigns.locum_api import LocumInterestListView, SyncLocumLeadsView
from apps.campaigns.views import CampaignViewSet

router = DefaultRouter()
router.register("campaigns", CampaignViewSet, basename="campaign")

urlpatterns = [
    path("appointments/", AppointmentListView.as_view(), name="appointment-list"),
    path("locum-interests/", LocumInterestListView.as_view(), name="locum-interest-list"),
    path("campaigns/<uuid:pk>/sync-locum/", SyncLocumLeadsView.as_view(), name="campaign-sync-locum"),
    path("campaigns/<uuid:pk>/agent/", CampaignAgentView.as_view(), name="campaign-agent"),
    path("campaigns/<uuid:pk>/agent/publish/", CampaignAgentPublishView.as_view(), name="campaign-agent-publish"),
    *router.urls,
]

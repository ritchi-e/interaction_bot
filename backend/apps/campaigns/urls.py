from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.agents.views import CampaignAgentPublishView, CampaignAgentView
from apps.campaigns.views import CampaignViewSet

router = DefaultRouter()
router.register("campaigns", CampaignViewSet, basename="campaign")

urlpatterns = [
    path("campaigns/<uuid:pk>/agent/", CampaignAgentView.as_view(), name="campaign-agent"),
    path("campaigns/<uuid:pk>/agent/publish/", CampaignAgentPublishView.as_view(), name="campaign-agent-publish"),
    *router.urls,
]

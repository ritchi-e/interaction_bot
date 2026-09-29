from django.urls import path

from apps.campaigns.views import InternalCampaignContextView, InternalViolationView

urlpatterns = [
    path("campaigns/<uuid:campaign_id>/context/", InternalCampaignContextView.as_view(), name="internal-context"),
    path("violations/", InternalViolationView.as_view(), name="internal-violation"),
]

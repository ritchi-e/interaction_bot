from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agents.models import AgentProfile
from apps.agents.publish import publish_agent
from apps.agents.serializers import AgentProfileSerializer
from apps.calls.dograh import DograhError
from apps.campaigns.models import Campaign


def _campaign(request, pk):
    return get_object_or_404(
        Campaign.objects.select_related("context", "organisation"),
        pk=pk,
        organisation=request.user.organisation,
    )


class CampaignAgentView(APIView):
    def get(self, request, pk):
        campaign = _campaign(request, pk)
        profile, _created = AgentProfile.objects.get_or_create(campaign=campaign)
        return Response(AgentProfileSerializer(profile).data)

    def put(self, request, pk):
        campaign = _campaign(request, pk)
        profile, _created = AgentProfile.objects.get_or_create(campaign=campaign)
        serializer = AgentProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CampaignAgentPublishView(APIView):
    def post(self, request, pk):
        campaign = _campaign(request, pk)
        profile, _created = AgentProfile.objects.get_or_create(campaign=campaign)
        try:
            publish_agent(profile)
        except (ValueError, DograhError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        profile.refresh_from_db()
        return Response(AgentProfileSerializer(profile).data)

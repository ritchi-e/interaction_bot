from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.campaigns.providers import dograh_model_configuration
from apps.tenants.serializers import (
    BusinessProfileSerializer,
    LoginSerializer,
    ProviderKeysSerializer,
    RegisterSerializer,
    UserSerializer,
    WhatsAppCallingSerializer,
    WhatsAppConnectionSerializer,
)
from apps.tenants.services import create_organisation


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = create_organisation(
            serializer.validated_data["organisation_name"],
            serializer.validated_data["email"],
            serializer.validated_data["password"],
        )
        token = Token.objects.create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            email=serializer.validated_data["email"].lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": "Invalid email or password."}, status=status.HTTP_400_BAD_REQUEST)
        token, _created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class _OrgRecordView(APIView):
    permission_classes = [IsAuthenticated]
    model = None
    serializer_class = None
    related_name = ""

    def _record(self, request):
        organisation = request.user.organisation
        if organisation is None:
            return None
        return getattr(organisation, self.related_name)

    def get(self, request):
        record = self._record(request)
        if record is None:
            return Response({"detail": "No organisation."}, status=status.HTTP_400_BAD_REQUEST)
        data = self.serializer_class(record).data
        if self.related_name == "provider_keys":
            data["dograh_configuration"] = dograh_model_configuration(record)
        if self.related_name == "whatsapp":
            data["webhook_path"] = f"/webhooks/whatsapp/{request.user.organisation.slug}/"
            data["dograh_webhook_path"] = f"/webhooks/dograh/{request.user.organisation.slug}/"
        return Response(data)

    def put(self, request):
        record = self._record(request)
        if record is None:
            return Response({"detail": "No organisation."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(record, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.get(request)


class WhatsAppSettingsView(_OrgRecordView):
    serializer_class = WhatsAppConnectionSerializer
    related_name = "whatsapp"


class WhatsAppCallingSettingsView(_OrgRecordView):
    serializer_class = WhatsAppCallingSerializer
    related_name = "whatsapp_calling"


class WhatsAppCallingEnableView(APIView):
    def post(self, request):
        organisation = request.user.organisation
        calling = getattr(organisation, "whatsapp_calling", None)
        connection = getattr(organisation, "whatsapp", None)
        if calling is None or connection is None:
            return Response({"detail": "No organisation."}, status=status.HTTP_400_BAD_REQUEST)
        from apps.whatsapp.asterisk import write_endpoints
        from apps.whatsapp.calling import enable_calling, fetch_sip_password
        from apps.tenants.models import WhatsAppCalling

        try:
            enable_calling(connection, calling)
            fetch_sip_password(connection, calling)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if request.data.get("business_number_e164"):
            calling.business_number_e164 = request.data["business_number_e164"]
            calling.save(update_fields=["business_number_e164", "updated_at"])
        write_endpoints(WhatsAppCalling.objects.exclude(sip_password=""))
        return Response(WhatsAppCallingSerializer(calling).data)


class ProviderSettingsView(_OrgRecordView):
    serializer_class = ProviderKeysSerializer
    related_name = "provider_keys"


class ProfileSettingsView(APIView):
    def get(self, request):
        profile = getattr(request.user.organisation, "profile", None)
        if profile is None:
            return Response({"detail": "No organisation."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BusinessProfileSerializer(profile).data)

    def put(self, request):
        profile = getattr(request.user.organisation, "profile", None)
        serializer = BusinessProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

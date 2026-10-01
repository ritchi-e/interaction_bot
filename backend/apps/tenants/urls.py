from django.urls import path

from apps.tenants.views import (
    LoginView,
    MeView,
    PlivoSettingsView,
    ProfileSettingsView,
    ProviderSettingsView,
    RegisterView,
    WhatsAppCallingEnableView,
    WhatsAppCallingSettingsView,
    WhatsAppSettingsView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("settings/whatsapp/", WhatsAppSettingsView.as_view(), name="settings-whatsapp"),
    path("settings/whatsapp-calling/", WhatsAppCallingSettingsView.as_view(), name="settings-whatsapp-calling"),
    path("settings/whatsapp-calling/enable/", WhatsAppCallingEnableView.as_view(), name="settings-whatsapp-calling-enable"),
    path("settings/plivo/", PlivoSettingsView.as_view(), name="settings-plivo"),
    path("settings/providers/", ProviderSettingsView.as_view(), name="settings-providers"),
    path("settings/profile/", ProfileSettingsView.as_view(), name="settings-profile"),
]

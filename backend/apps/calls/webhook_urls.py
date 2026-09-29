from django.urls import path

from apps.calls.views import DograhWebhookView

urlpatterns = [
    path("dograh/<slug:slug>/", DograhWebhookView.as_view(), name="dograh-webhook"),
]

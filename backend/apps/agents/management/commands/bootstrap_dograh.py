"""PUT the shared Dograh org's base model configuration once.

Every business currently authenticates with the same platform Dograh API
key (settings.DOGRAH_API_KEY), so they all share one Dograh org and one base
model configuration. Each campaign's own STT language and TTS voice/provider
still differ — those travel per-workflow as ``workflow_configurations.model_
overrides`` (see apps/agents/model_overrides.py and apps/agents/publish.py),
computed and sent automatically every time an agent is published.

This command only sets the shared base underneath those overrides: language
model via the context guard, Deepgram STT, and Rumik TTS. A campaign's
language picks the Rumik voice. Businesses do not choose a voice provider
or paste keys. Run it once per environment, and again any time the base
defaults change:

    python manage.py bootstrap_dograh
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.agents.dograh_admin import DograhAdmin
from apps.calls.dograh import DograhError


class Command(BaseCommand):
    help = "PUT the shared org-level Dograh model configuration (LLM/STT/TTS base defaults)."

    def handle(self, *args, **options):
        if not settings.DOGRAH_API_KEY:
            raise CommandError("DOGRAH_API_KEY is not set")

        config = {
            "version": 2,
            "mode": "byok",
            "byok": {
                "mode": "pipeline",
                "pipeline": {
                    "llm": {
                        "provider": "openai",
                        "model": os.environ.get("UPSTREAM_LLM_MODEL", "gpt-4o-mini"),
                        "api_key": "local",
                        "base_url": "http://context-guard:8080/v1",
                    },
                    "stt": {
                        "provider": "deepgram",
                        "model": "nova-3",
                        "language": "multi",
                        "api_key": settings.DEEPGRAM_API_KEY,
                    },
                    "tts": {
                        "provider": "openai",
                        "base_url": settings.RUMIK_BRIDGE_URL,
                        "model": "rumik-siya-hindi",
                        "voice": "alloy",
                        "api_key": settings.RUMIK_API_KEY or "bridge",
                    },
                    "embeddings": {
                        "provider": "openai",
                        "model": "text-embedding-3-small",
                        "api_key": os.environ.get("UPSTREAM_LLM_API_KEY", ""),
                    },
                },
            },
        }

        admin = DograhAdmin()
        try:
            admin.set_model_configuration(config)
        except DograhError as exc:
            raise CommandError(f"Dograh rejected the base model configuration: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("Dograh base model configuration saved."))

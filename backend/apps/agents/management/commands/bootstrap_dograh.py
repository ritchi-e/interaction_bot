"""PUT the shared Dograh org's base model configuration once.

Every business currently authenticates with the same platform Dograh API
key (settings.DOGRAH_API_KEY), so they all share one Dograh org and one base
model configuration. Each campaign's own STT language and TTS voice still
differ — those travel per-workflow as ``workflow_configurations.model_
overrides`` (see apps/agents/model_overrides.py and apps/agents/publish.py),
computed and sent automatically every time an agent is published.

This command only sets the shared base underneath those overrides: language
model via the context guard, self-hosted STT (Deepgram Flux protocol against
speech-stt), and self-hosted TTS (OpenAI speech API against speech-tts).

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

        token = (settings.SPEECH_API_TOKEN or "local").strip() or "local"
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
                        "model": "flux-general-multi",
                        "language": "hi",
                        "base_url": settings.SPEECH_STT_URL,
                        "api_key": token,
                    },
                    "tts": {
                        "provider": "openai",
                        "base_url": settings.SPEECH_TTS_URL,
                        "model": "selfhost-hi-female-indic",
                        "voice": "alloy",
                        "api_key": token,
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

"""What to paste into Dograh's model configuration for this deployment.

Speech-to-text and text-to-speech are self-hosted on the GPU. Dograh reaches
the language model only through the context guard.
"""

import os

from django.conf import settings


def dograh_model_configuration(keys):
    token = (settings.SPEECH_API_TOKEN or "local").strip() or "local"
    return {
        "llm": {
            "provider": "openai",
            "base_url": "http://context-guard:8080/v1",
            "model": os.environ.get("UPSTREAM_LLM_MODEL", "gpt-4o-mini"),
            "api_key": "local",
            "note": "Point Dograh at the context guard. The guard calls the hosted model with UPSTREAM_LLM_API_KEY.",
        },
        "stt": {
            "provider": "deepgram",
            "model": "flux-general-multi",
            "language": "hi",
            "base_url": settings.SPEECH_STT_URL,
            "api_key": token,
            "note": (
                "Self-hosted speech-stt (Nemotron Hinglish) speaking the "
                "Deepgram Flux protocol. Campaign overrides pin language "
                "hints; see apps/agents/model_overrides.py."
            ),
        },
        "tts": {
            "provider": "openai",
            "base_url": settings.SPEECH_TTS_URL,
            "model": "selfhost-hi-female-vits",
            "voice": "alloy",
            "api_key": token,
            "note": (
                "Self-hosted speech-tts. Hindi default is IndicTTS VITS. "
                "See apps/agents/model_overrides.py."
            ),
        },
        "telephony": {"provider": "plivo", "caller_id_format": "+91XXXXXXXXXX"},
    }

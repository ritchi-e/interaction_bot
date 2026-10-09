"""What to paste into Dograh's model configuration for this deployment.

Speech-to-text is Deepgram Flux. Speech is Voxtral behind the OpenAI-compatible
proxy. Dograh reaches the language model only through the context guard.
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
            "base_url": settings.DEEPGRAM_BASE_URL,
            "api_key": (settings.DEEPGRAM_API_KEY or "").strip() or token,
            "language_hints": ["hi", "en"],
            "note": (
                "Deepgram Flux cloud. Hindi campaigns also hint English so "
                "loanwords survive. See apps/agents/model_overrides.py."
            ),
        },
        "tts": {
            "provider": "openai",
            "base_url": settings.SPEECH_TTS_URL,
            "model": "hi_female",
            "voice": "alloy",
            "api_key": token,
            "note": (
                "Voxtral TTS via the OpenAI speech proxy. Hindi default is "
                "the hi_female preset. See apps/agents/model_overrides.py."
            ),
        },
        "telephony": {"provider": "plivo", "caller_id_format": "+91XXXXXXXXXX"},
    }

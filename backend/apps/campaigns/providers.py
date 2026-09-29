"""What to paste into Dograh's model configuration for this deployment.

Speech-to-text, text-to-speech, and the language model are all hosted APIs.
Dograh reaches the language model only through the context guard.
"""

import os

from django.conf import settings


def dograh_model_configuration(keys):
    tts_provider = keys.tts_provider or "sarvam"
    tts_models = {
        "sarvam": {"provider": "sarvam", "model": "bulbul:v2", "voice": keys.tts_voice or "anushka"},
        "cartesia": {"provider": "cartesia", "model": "sonic", "voice": keys.tts_voice or ""},
        "elevenlabs": {"provider": "elevenlabs", "model": "eleven_flash_v2_5", "voice": keys.tts_voice or ""},
        "rumik": {
            "provider": "rumik",
            "model": "streaming",
            "voice": keys.tts_voice or "",
            "note": "Rumik is not built into Dograh. Use deploy/dograh-overrides/rumik_tts.py.",
        },
    }
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
            "model": "nova-3",
            "language": "multi",
            "endpointing_ms": 300,
            "key_source": "tenant" if keys.deepgram_api_key else "platform",
            "platform_key_set": bool(settings.DEEPGRAM_API_KEY),
        },
        "tts": tts_models.get(tts_provider, tts_models["sarvam"]),
        "telephony": {"provider": "whatsapp", "caller_id_format": "+91XXXXXXXXXX"},
    }

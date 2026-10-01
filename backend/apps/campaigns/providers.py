"""What to paste into Dograh's model configuration for this deployment.

Speech-to-text, text-to-speech, and the language model are all hosted APIs.
Dograh reaches the language model only through the context guard.
"""

import os

from django.conf import settings


def dograh_model_configuration(keys):
    tts_provider = keys.tts_provider or "rumik"
    tts_models = {
        "sarvam": {"provider": "sarvam", "model": "bulbul:v2", "voice": keys.tts_voice or "anushka"},
        "cartesia": {"provider": "cartesia", "model": "sonic", "voice": keys.tts_voice or ""},
        "elevenlabs": {"provider": "elevenlabs", "model": "eleven_flash_v2_5", "voice": keys.tts_voice or ""},
        "rumik": {
            "provider": "openai",
            "base_url": settings.RUMIK_BRIDGE_URL,
            "model": "rumik-siya-hindi",
            "note": (
                "Routed through the rumik-bridge service, an OpenAI-compatible "
                "facade in front of Rumik's streaming voice (low first-audio "
                "latency). `model` picks a language preset per campaign; see "
                "apps/agents/model_overrides.py."
            ),
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
            "note": (
                "This is the org-level default. Each campaign's published "
                "workflow overrides the language (hi/en/multi) to match its "
                "own Campaign.language; see apps/agents/model_overrides.py."
            ),
        },
        "tts": tts_models.get(tts_provider, tts_models["sarvam"]),
        "telephony": {"provider": "plivo", "caller_id_format": "+91XXXXXXXXXX"},
    }

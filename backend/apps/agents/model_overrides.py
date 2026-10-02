"""Per-campaign Dograh model overrides: STT language and TTS voice.

Dograh's org-level model configuration is shared by the whole platform (one
Dograh account owns every business's workflow, authenticated with the
platform API key). A campaign's own speech-to-text language and voice
therefore travel as a per-workflow ``workflow_configurations.model_overrides``
layered on top of that shared base — the same mechanism (and the same
streaming Rumik bridge) proven out in the local viva tester's two
test workflows.

Unlike that script, no STT keyterm dictionary is set here: those calls are
about a viva project vocabulary, real calls are about a business's own offer,
and there is no fixed small vocabulary worth biasing every business toward.

Every override below is self-contained (it always carries its own
``api_key``), rather than relying on Dograh to inherit one from the shared
org base. Dograh only auto-fills a missing override api_key when the
override's provider matches the org base's own provider for that section
(see dograh/api/services/configuration/resolve.py::enrich_overrides_with_api_keys);
a campaign is free to pick a TTS provider different from whatever the base
happens to be configured with, so that inheritance cannot be relied on.
"""

from django.conf import settings

# Callers mix languages even when the campaign is Hindi or English: a Hindi
# call often ends with "thank you", and an English call still has Hindi words.
# Deepgram "multi" is the code-switching model, which is what the Hinglish
# campaigns already used. Pinning Hindi to "hi" dropped those English words.
def stt_language_for(campaign_language):
    return "multi"


# Matches the presets in context_guard/rumik_bridge.py. Hindi uses the
# Hinglish delivery so English words inside a Hindi sentence (a sale name,
# "thank you") are spoken as English instead of being forced through Hindi
# phonetics. Indian English stays on its own preset.
_RUMIK_VOICE_MODEL = {
    "hi": "rumik-siya-hinglish",
    "en_in": "rumik-siya-english-indian",
    "hinglish": "rumik-siya-hinglish",
}

# Sarvam Bulbul's own language codes, used only when a campaign (or the
# organisation default) picked Sarvam instead of Rumik.
_SARVAM_LANGUAGE = {
    "hi": "hi-IN",
    "en_in": "en-IN",
    "hinglish": "hi-IN",
}


def rumik_voice_model_for(campaign_language):
    return _RUMIK_VOICE_MODEL.get(campaign_language, "rumik-siya-hinglish")


def selected_tts(campaign, keys=None):
    """Provider and voice the campaign will actually speak with.

    ``keys.tts_voice`` belongs to ``keys.tts_provider``. It is only a fallback
    when this campaign ends up on that same provider.
    """

    provider = campaign.tts_provider or (keys.tts_provider if keys else "") or "rumik"
    org_voice = keys.tts_voice if (keys and keys.tts_provider == provider) else ""
    voice = (campaign.tts_voice or org_voice or "").strip()
    return provider, voice


def spoken_voice_name(campaign, keys=None):
    """Speaker name the caller hears, for matching Hindi verb gender to the voice.

    Rumik speaks as RUMIK_TTS_DEFAULT_SPEAKER (Siya when that is unset),
    regardless of any leftover voice name from another provider. Sarvam with
    no voice picked speaks as Anushka, the
    platform default in the shared Dograh base configuration.
    """

    provider, voice = selected_tts(campaign, keys)
    if provider == "rumik":
        return (settings.RUMIK_TTS_DEFAULT_SPEAKER or "siya").strip().lower() or "siya"
    if provider == "sarvam":
        return (voice or "anushka").lower()
    return voice.lower()


def _tenant_or_platform_key(keys, provider):
    tenant_key = keys.key_for(provider) if keys else ""
    if tenant_key:
        return tenant_key
    return {
        "sarvam": settings.SARVAM_API_KEY,
        "rumik": settings.RUMIK_API_KEY,
        "cartesia": settings.CARTESIA_API_KEY,
        "elevenlabs": settings.ELEVENLABS_API_KEY,
    }.get(provider, "")


def _stt_override(campaign, keys):
    api_key = (keys.deepgram_api_key if keys else "") or settings.DEEPGRAM_API_KEY
    if campaign.language == "hi":
        # Flux reports the end of the turn itself. Dograh then stops waiting on
        # its own silence timer. language "hi" is only a hint: the model is the
        # multilingual one, so an English word inside Hindi is still transcribed.
        override = {
            "provider": "deepgram",
            "model": "flux-general-multi",
            "language": "hi",
        }
    else:
        # This Dograh build fixes Nova endpointing at 100ms inside its speech
        # service. A campaign override cannot change that number.
        override = {"provider": "deepgram", "language": stt_language_for(campaign.language)}
    if api_key:
        override["api_key"] = api_key
    return override


def _tts_override(campaign, keys):
    provider, voice = selected_tts(campaign, keys)

    if provider == "rumik":
        # Voice travels through Dograh's `model` field, not `voice`: pipecat's
        # OpenAI TTS client only accepts a fixed set of OpenAI voice names in
        # `voice`, but passes `model` straight through with no allow-list. See
        # context_guard/rumik_bridge.py for how the bridge reads it back. The
        # bridge itself never checks this api_key (it authenticates to Rumik
        # with its own RUMIK_API_KEY), but Dograh's schema requires a
        # non-empty value here regardless.
        return {
            "provider": "openai",
            "base_url": settings.RUMIK_BRIDGE_URL,
            "model": rumik_voice_model_for(campaign.language),
            "voice": "alloy",
            "api_key": _tenant_or_platform_key(keys, "rumik") or "bridge",
        }

    if provider == "sarvam":
        api_key = _tenant_or_platform_key(keys, "sarvam")
        if not api_key:
            return None
        override = {
            "provider": "sarvam",
            "language": _SARVAM_LANGUAGE.get(campaign.language, "hi-IN"),
            "api_key": api_key,
        }
        if voice:
            override["voice"] = voice
        return override

    if provider in ("cartesia", "elevenlabs"):
        api_key = _tenant_or_platform_key(keys, provider)
        if not (voice and api_key):
            return None
        return {"provider": provider, "voice": voice, "api_key": api_key}

    return None


def rumik_bridge_target(campaign, keys=None):
    """(base_url, model) the campaign's greeting will be spoken with, or None.

    Only Rumik runs through our own bridge and can be asked to start
    synthesizing ahead of pickup; every other provider talks straight to its
    own vendor from inside Dograh and offers us no pre-warm hook.
    """

    override = _tts_override(campaign, keys)
    if not override or override.get("provider") != "openai":
        return None
    return override.get("base_url"), override.get("model")


def build_model_overrides(campaign, keys=None):
    """Workflow-level overrides layered onto the shared org model configuration.

    Always overrides STT language, since that depends on the campaign
    regardless of which TTS provider is in play. Only overrides TTS when
    there is a usable, fully self-contained configuration to send (a known
    provider with an available API key).
    """

    overrides = {"stt": _stt_override(campaign, keys)}
    tts_override = _tts_override(campaign, keys)
    if tts_override:
        overrides["tts"] = tts_override
    return {"model_overrides": overrides}

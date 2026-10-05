"""Per-campaign Dograh model overrides: self-hosted STT language and TTS voice.

Dograh's org-level model configuration is shared by the whole platform. A
campaign's speech language and voice travel as a per-workflow
``workflow_configurations.model_overrides`` layered on top of that shared base.

STT talks the Deepgram Flux protocol to our ``speech-stt`` container
(Nemotron). TTS talks the OpenAI speech API to ``speech-tts`` (Piper VITS for Hindi,
dhee-indic-f5 for English / quality fallback) using system voice IDs.
Hindi campaigns already allow English loanwords (code-switching); there is no
separate Hinglish language mode.
"""

from django.conf import settings

# System voices shipped in speech/tts/voices/voices.json. Users pick gender in
# the UI; language comes from the campaign. Hindi defaults to Piper VITS
# (*-fast) for sub-second latency; English stays on F5 (no Piper en_in voice).
_VOICE_IDS = {
    ("hi", "female"): "selfhost-hi-female-fast",
    ("hi", "male"): "selfhost-hi-male-fast",
    ("en_in", "female"): "selfhost-en-female",
    ("en_in", "male"): "selfhost-en-male",
}

_VALID_GENDERS = frozenset({"female", "male"})


def voice_gender(campaign) -> str:
    raw = (getattr(campaign, "tts_voice", None) or "").strip().lower()
    if raw in _VALID_GENDERS:
        return raw
    # Legacy cloud voice names still stored on older rows.
    if raw in {"abhilash", "karun", "saurabh", "rahul", "arjun", "vikram", "amit"}:
        return "male"
    return "female"


def voice_preset_for(campaign) -> str:
    """TTS model id Dograh sends; speech-tts maps it to a system voice."""
    lang = campaign.language if campaign.language in ("hi", "en_in") else "hi"
    return _VOICE_IDS[(lang, voice_gender(campaign))]


def spoken_voice_name(campaign, keys=None):
    """Gender token used for Hindi verb agreement in the prompt compiler."""
    return voice_gender(campaign)


def _speech_token():
    return (settings.SPEECH_API_TOKEN or "local").strip() or "local"


def _stt_override(campaign):
    # Hindi uses language hint "hi"; the STT server maps that to Nemotron's
    # auto prompt so English words inside Hindi still transcribe.
    language = "en" if campaign.language == "en_in" else "hi"
    return {
        "provider": "deepgram",
        "model": "flux-general-multi",
        "language": language,
        "base_url": settings.SPEECH_STT_URL,
        "api_key": _speech_token(),
    }


def _tts_override(campaign):
    return {
        "provider": "openai",
        "base_url": settings.SPEECH_TTS_URL,
        "model": voice_preset_for(campaign),
        "voice": "alloy",
        "api_key": _speech_token(),
    }


def tts_prewarm_target(campaign, keys=None):
    override = _tts_override(campaign)
    return override.get("base_url"), override.get("model")


rumik_bridge_target = tts_prewarm_target


def rumik_voice_model_for(campaign_or_language):
    """Back-compat: accept a campaign or a bare language code."""
    if hasattr(campaign_or_language, "language"):
        return voice_preset_for(campaign_or_language)

    class _Tmp:
        language = campaign_or_language if campaign_or_language in ("hi", "en_in") else "hi"
        tts_voice = "female"

    return voice_preset_for(_Tmp())


def build_model_overrides(campaign, keys=None):
    # max_user_idle_timeout: with Piper Hindi TTS, bot speech finishes quickly.
    # 12s is enough for the caller to answer after the greeting; 30s felt like
    # a dead line when STT missed the first reply.
    return {
        "max_user_idle_timeout": 12.0,
        "model_overrides": {
            "stt": _stt_override(campaign),
            "tts": _tts_override(campaign),
        },
    }

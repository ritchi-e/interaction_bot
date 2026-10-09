"""Per-campaign Dograh model overrides: Deepgram Flux STT and Voxtral TTS.

Dograh's org-level model configuration is shared by the whole platform. A
campaign's speech language and voice travel as a per-workflow
``workflow_configurations.model_overrides`` layered on top of that shared base.

STT is Deepgram Flux cloud (``flux-general-multi``). Hindi campaigns also
send an English hint so loanwords such as loan, car, and thank you survive.
TTS talks the OpenAI speech API to the Voxtral proxy, which maps the model id
onto a Voxtral preset (``hi_female`` / ``hi_male``).
"""

from django.conf import settings

# Model ids the Voxtral proxy understands. Users pick gender in the UI;
# language comes from the campaign.
_VOICE_IDS = {
    ("hi", "female"): "hi_female",
    ("hi", "male"): "hi_male",
    ("en_in", "female"): "en_female",
    ("en_in", "male"): "en_male",
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
    language = "en" if campaign.language == "en_in" else "hi"
    # flux-general-multi code-switches when both languages are hinted.
    hints = ["en"] if language == "en" else ["hi", "en"]
    return {
        "provider": "deepgram",
        "model": "flux-general-multi",
        "language": language,
        "language_hints": hints,
        "base_url": settings.DEEPGRAM_BASE_URL,
        "api_key": (settings.DEEPGRAM_API_KEY or "").strip() or "missing",
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
    # max_user_idle_timeout: 12s is enough for the caller to answer after the
    # greeting; 30s felt like a dead line when STT missed the first reply.
    return {
        "max_user_idle_timeout": 12.0,
        "model_overrides": {
            "stt": _stt_override(campaign),
            "tts": _tts_override(campaign),
        },
    }

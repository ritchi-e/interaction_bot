import pytest
from django.conf import settings

from apps.agents.model_overrides import build_model_overrides, voice_preset_for
from apps.campaigns.models import Campaign
from apps.tenants.services import create_organisation


def _campaign(language, tts_voice="female"):
    user = create_organisation(
        "Sundaram Loans",
        f"ops-{language}-{tts_voice}@sundaram.test",
        "supersecret1",
    )
    campaign = Campaign.objects.create(
        organisation=user.organisation,
        name="Loans",
        language=language,
        tts_voice=tts_voice,
    )
    return campaign, user.organisation.provider_keys


@pytest.mark.django_db
@pytest.mark.parametrize(
    "language,stt_language",
    [("en_in", "en"), ("hi", "hi")],
)
def test_stt_language_follows_campaign_language(language, stt_language):
    campaign, keys = _campaign(language)
    stt = build_model_overrides(campaign, keys)["model_overrides"]["stt"]
    assert stt["provider"] == "deepgram"
    assert stt["model"] == "flux-general-multi"
    assert stt["language"] == stt_language
    assert stt["base_url"] == settings.SPEECH_STT_URL
    assert stt["api_key"]


@pytest.mark.django_db
def test_hindi_listens_with_flux_against_selfhosted_stt():
    campaign, keys = _campaign("hi")
    stt = build_model_overrides(campaign, keys)["model_overrides"]["stt"]
    assert stt["provider"] == "deepgram"
    assert stt["model"] == "flux-general-multi"
    assert stt["language"] == "hi"


@pytest.mark.django_db
def test_no_dictionary_is_ever_sent():
    campaign, keys = _campaign("hi")
    overrides = build_model_overrides(campaign, keys)
    assert "dictionary" not in overrides


@pytest.mark.django_db
@pytest.mark.parametrize(
    "language,voice,model",
    [
        ("hi", "female", "selfhost-hi-female-vits"),
        ("hi", "male", "selfhost-hi-male-vits"),
        ("en_in", "female", "selfhost-en-female"),
        ("en_in", "male", "selfhost-en-male"),
    ],
)
def test_system_voice_follows_language_and_gender(language, voice, model):
    campaign, keys = _campaign(language, tts_voice=voice)
    tts = build_model_overrides(campaign, keys)["model_overrides"]["tts"]
    assert tts["provider"] == "openai"
    assert tts["model"] == model
    assert tts["base_url"] == settings.SPEECH_TTS_URL
    assert voice_preset_for(campaign) == model


@pytest.mark.django_db
def test_tts_override_always_self_contained():
    campaign, keys = _campaign("hi")
    overrides = build_model_overrides(campaign, keys)
    assert overrides["model_overrides"]["tts"]["api_key"]

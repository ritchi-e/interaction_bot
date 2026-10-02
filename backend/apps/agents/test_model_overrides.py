import pytest

from apps.agents.model_overrides import build_model_overrides
from apps.campaigns.models import Campaign
from apps.tenants.services import create_organisation


def _campaign(language, tts_provider="", tts_voice=""):
    user = create_organisation("Sundaram Loans", f"ops-{language}-{tts_provider}@sundaram.test", "supersecret1")
    campaign = Campaign.objects.create(
        organisation=user.organisation,
        name="Loans",
        language=language,
        tts_provider=tts_provider,
        tts_voice=tts_voice,
    )
    return campaign, user.organisation.provider_keys


@pytest.mark.django_db
@pytest.mark.parametrize(
    "language,stt_language",
    [("en_in", "multi"), ("hinglish", "multi")],
)
def test_stt_language_follows_campaign_language(language, stt_language):
    campaign, keys = _campaign(language)
    overrides = build_model_overrides(campaign, keys)
    assert overrides["model_overrides"]["stt"]["provider"] == "deepgram"
    assert overrides["model_overrides"]["stt"]["language"] == stt_language
    assert "model" not in overrides["model_overrides"]["stt"]


@pytest.mark.django_db
def test_hindi_listens_with_flux_so_deepgram_ends_the_turn():
    campaign, keys = _campaign("hi")
    stt = build_model_overrides(campaign, keys)["model_overrides"]["stt"]
    assert stt["provider"] == "deepgram"
    assert stt["model"] == "flux-general-multi"
    assert stt["language"] == "hi"


@pytest.mark.django_db
def test_no_dictionary_is_ever_sent():
    # Unlike the local viva tester, production calls have no fixed
    # small vocabulary to bias toward, so no keyterm dictionary is set.
    campaign, keys = _campaign("hinglish")
    overrides = build_model_overrides(campaign, keys)
    assert "dictionary" not in overrides


@pytest.mark.django_db
@pytest.mark.parametrize(
    "language,model",
    [("hi", "rumik-siya-hinglish"), ("en_in", "rumik-siya-english-indian"), ("hinglish", "rumik-siya-hinglish")],
)
def test_rumik_voice_preset_follows_campaign_language(language, model):
    campaign, keys = _campaign(language, tts_provider="rumik")
    overrides = build_model_overrides(campaign, keys)
    tts = overrides["model_overrides"]["tts"]
    assert tts["provider"] == "openai"
    assert tts["model"] == model
    # The bridge doesn't check this, but Dograh's own schema requires it.
    assert tts["api_key"]


@pytest.mark.django_db
def test_rumik_tts_override_is_self_contained_even_without_a_tenant_key():
    # No sarvam/rumik/cartesia/elevenlabs key was ever set on this org, so
    # Rumik falls back to the platform-level RUMIK_API_KEY (or a harmless
    # placeholder) rather than sending a blank api_key Dograh would reject.
    campaign, keys = _campaign("hi", tts_provider="rumik")
    overrides = build_model_overrides(campaign, keys)
    assert overrides["model_overrides"]["tts"]["api_key"]


@pytest.mark.django_db
def test_sarvam_tts_override_carries_language_and_voice():
    campaign, keys = _campaign("hi", tts_provider="sarvam", tts_voice="anushka")
    keys.sarvam_api_key = "sarvam-secret"
    keys.save()
    overrides = build_model_overrides(campaign, keys)
    assert overrides["model_overrides"]["tts"] == {
        "provider": "sarvam",
        "language": "hi-IN",
        "voice": "anushka",
        "api_key": "sarvam-secret",
    }


@pytest.mark.django_db
def test_no_tts_override_when_provider_has_no_api_key_available():
    # Cartesia needs a real key. With none on the org and none at the
    # platform level, there is nothing self-contained to send, so the org's
    # own base config decides instead.
    campaign, keys = _campaign("hi", tts_provider="cartesia", tts_voice="some-voice-id")
    overrides = build_model_overrides(campaign, keys)
    assert "tts" not in overrides["model_overrides"]


@pytest.mark.django_db
def test_no_tts_override_when_voice_provider_has_no_voice_picked():
    # Cartesia/ElevenLabs need an explicit voice id; with none picked there
    # is nothing useful to override even if a key exists.
    campaign, keys = _campaign("hi", tts_provider="cartesia")
    keys.cartesia_api_key = "cartesia-secret"
    keys.save()
    overrides = build_model_overrides(campaign, keys)
    assert "tts" not in overrides["model_overrides"]


@pytest.mark.django_db
def test_unset_provider_uses_rumik_for_the_campaign_language():
    campaign, keys = _campaign("hi")
    overrides = build_model_overrides(campaign, keys)
    tts = overrides["model_overrides"]["tts"]
    assert tts["provider"] == "openai"
    assert tts["model"] == "rumik-siya-hinglish"

import pytest

from apps.agents.definition import build_workflow_definition
from apps.agents.models import AgentProfile
from apps.agents.node_spec import check_definition
from apps.agents.publish import publish_agent, validate_spoken_lines
from apps.campaigns.models import Campaign
from apps.campaigns.prompt_compiler import MINIMAL_DOGRAH_PROMPT, compile_system_prompt
from apps.tenants.services import create_organisation


def _campaign():
    user = create_organisation("Sundaram Loans", "ops@sundaram.test", "supersecret1")
    campaign = Campaign.objects.create(organisation=user.organisation, name="Loans", language="hi")
    campaign.context.offer_details = "Processing fee is Rs 499."
    campaign.context.save()
    return campaign


@pytest.mark.django_db
def test_definition_has_one_start_and_minimal_prompt():
    campaign = _campaign()
    profile = AgentProfile.objects.create(campaign=campaign, greeting="Hello.", closing_line="Goodbye.")
    definition = build_workflow_definition(profile, webhook_url="https://example.test/hook", webhook_token="tok")
    check_definition(definition)
    starts = [node for node in definition["nodes"] if node["type"] == "startCall"]
    assert len(starts) == 1
    agent = next(node for node in definition["nodes"] if node["type"] == "agentNode")
    assert agent["data"]["prompt"] == MINIMAL_DOGRAH_PROMPT


@pytest.mark.django_db
def test_greeting_with_unknown_price_is_rejected():
    campaign = _campaign()
    with pytest.raises(ValueError):
        validate_spoken_lines(campaign, "The fee is Rs 999.")


@pytest.mark.django_db
def test_publish_updates_existing_workflow(monkeypatch):
    campaign = _campaign()
    profile = AgentProfile.objects.create(
        campaign=campaign, greeting="Hello.", closing_line="Goodbye.", dograh_workflow_id=7
    )
    called = {}

    def update(self, workflow_id, name, definition, workflow_configurations=None):
        called["id"] = workflow_id
        called["workflow_configurations"] = workflow_configurations
        return {"id": workflow_id, "uuid": "wf-uuid"}

    monkeypatch.setattr("apps.agents.publish.DograhAdmin.update_workflow", update)
    monkeypatch.setattr("apps.agents.publish.DograhAdmin.create_workflow", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("create")))
    monkeypatch.setattr("apps.agents.publish.DograhAdmin.release_workflow", lambda self, workflow_id: "wf-uuid")
    publish_agent(profile)
    assert called["id"] == 7
    profile.refresh_from_db()
    assert profile.dograh_workflow_uuid == "wf-uuid"
    # The Hindi campaign in _campaign() gets Deepgram STT pinned to "hi" and
    # no keyterm dictionary (unlike the viva script's per-workflow overrides).
    overrides = called["workflow_configurations"]["model_overrides"]
    assert overrides["stt"]["provider"] == "deepgram"
    assert overrides["stt"]["language"] == "hi"
    assert "dictionary" not in called["workflow_configurations"]


@pytest.mark.django_db
def test_role_is_in_the_compiled_prompt():
    campaign = _campaign()
    AgentProfile.objects.create(campaign=campaign, role="loan advisor", persona="Warm and brief.")
    prompt = compile_system_prompt(campaign)
    assert "loan advisor" in prompt
    assert "Warm and brief." in prompt


@pytest.mark.django_db
def test_hindi_prompt_locks_feminine_forms_for_the_default_voice():
    campaign = _campaign()
    prompt = compile_system_prompt(campaign)
    assert "समझ गई" in prompt
    assert "Never use masculine forms for yourself" in prompt


@pytest.mark.django_db
def test_hinglish_rumik_voice_stays_feminine_even_if_a_male_name_is_stored():
    campaign = _campaign()
    campaign.language = "hinglish"
    campaign.tts_provider = "rumik"
    campaign.tts_voice = "abhilash"
    campaign.save()
    prompt = compile_system_prompt(campaign)
    assert "You are a woman." in prompt
    assert "समझ गई" in prompt


@pytest.mark.django_db
def test_male_sarvam_voice_locks_masculine_forms():
    campaign = _campaign()
    campaign.tts_provider = "sarvam"
    campaign.tts_voice = "abhilash"
    campaign.save()
    prompt = compile_system_prompt(campaign)
    assert "You are a man." in prompt
    assert "समझ गया" in prompt
    assert "Never use feminine forms for yourself" in prompt


@pytest.mark.django_db
def test_english_prompt_has_no_hindi_gender_rule():
    campaign = _campaign()
    campaign.language = "en_in"
    campaign.save()
    prompt = compile_system_prompt(campaign)
    assert "समझ गई" not in prompt
    assert "You are a woman." not in prompt

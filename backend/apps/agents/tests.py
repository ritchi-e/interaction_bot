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

    def update(self, workflow_id, name, definition):
        called["id"] = workflow_id
        return {"id": workflow_id, "uuid": "wf-uuid"}

    monkeypatch.setattr("apps.agents.publish.DograhAdmin.update_workflow", update)
    monkeypatch.setattr("apps.agents.publish.DograhAdmin.create_workflow", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("create")))
    publish_agent(profile)
    assert called["id"] == 7
    profile.refresh_from_db()
    assert profile.dograh_workflow_uuid == "wf-uuid"


@pytest.mark.django_db
def test_role_is_in_the_compiled_prompt():
    campaign = _campaign()
    AgentProfile.objects.create(campaign=campaign, role="loan advisor", persona="Warm and brief.")
    prompt = compile_system_prompt(campaign)
    assert "loan advisor" in prompt
    assert "Warm and brief." in prompt

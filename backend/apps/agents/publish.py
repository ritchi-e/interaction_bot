import sys
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from apps.agents.definition import build_workflow_definition
from apps.agents.dograh_admin import DograhAdmin
from apps.agents.model_overrides import build_model_overrides
from apps.calls.dograh import DograhError
from apps.campaigns.prompt_compiler import facts_block


def _guard():
    root = Path(__file__).resolve().parents[3]
    guard_path = str(root / "context_guard")
    if guard_path not in sys.path:
        sys.path.insert(0, guard_path)
    from guard import validate_sentence

    return validate_sentence


def validate_spoken_lines(campaign, *lines):
    context = campaign.context
    profile = getattr(campaign.organisation, "profile", None)
    business_name = profile.display_name if profile and profile.display_name else campaign.organisation.name
    facts = facts_block(context, business_name)
    forbidden = context.forbidden_topics or []
    competitors = context.competitors or []
    validate_sentence = _guard()
    for line in lines:
        text = (line or "").strip()
        if not text:
            raise ValueError("Greeting and closing line are required")
        ok, reason = validate_sentence(text, facts, forbidden, competitors)
        if not ok:
            raise ValueError(f"Rejected spoken line ({reason}): {text}")


def publish_agent(profile):
    campaign = profile.campaign
    organisation = campaign.organisation
    calling = getattr(organisation, "whatsapp_calling", None)
    if calling is None or not calling.webhook_token:
        raise ValueError("This business has no Dograh webhook token yet")
    validate_spoken_lines(campaign, profile.greeting, profile.closing_line)
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    definition = build_workflow_definition(
        profile,
        webhook_url=f"{base}/webhooks/dograh/{organisation.slug}/",
        webhook_token=calling.webhook_token,
    )
    keys = getattr(organisation, "provider_keys", None)
    admin = DograhAdmin(api_key=(keys.dograh_api_key if keys and keys.dograh_api_key else None))
    workflow_configurations = build_model_overrides(campaign, keys)
    try:
        if profile.dograh_workflow_id:
            result = admin.update_workflow(
                profile.dograh_workflow_id, campaign.name, definition, workflow_configurations
            )
        else:
            result = admin.create_workflow(campaign.name, definition, workflow_configurations)
    except DograhError as exc:
        profile.publish_error = str(exc)
        profile.save(update_fields=["publish_error", "updated_at"])
        raise
    if result.get("id"):
        profile.dograh_workflow_id = int(result["id"])
    if result.get("uuid"):
        profile.dograh_workflow_uuid = result["uuid"]
        campaign.dograh_workflow_uuid = result["uuid"]
        campaign.save(update_fields=["dograh_workflow_uuid", "updated_at"])
    profile.last_published_at = timezone.now()
    profile.publish_error = ""
    profile.save()
    return profile

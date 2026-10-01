"""Push a business's Plivo caller line into Dograh."""

from apps.agents.dograh_admin import DograhAdmin
from apps.calls.dograh import DograhError


def sync_plivo_line(line):
    if not line.auth_id or not line.auth_token or not line.caller_id:
        raise ValueError("Plivo Auth ID, Auth Token, and caller ID are required")
    keys = getattr(line.organisation, "provider_keys", None)
    admin = DograhAdmin(api_key=(keys.dograh_api_key if keys and keys.dograh_api_key else None))
    name = f"plivo-{line.organisation.slug}"[:64]
    try:
        saved = admin.save_plivo_line(
            name=name,
            auth_id=line.auth_id,
            auth_token=line.auth_token,
            caller_id=line.caller_id,
            config_id=line.dograh_config_id,
            phone_number_id=line.dograh_phone_number_id,
        )
    except DograhError as exc:
        raise ValueError(str(exc)) from exc
    line.dograh_config_id = saved.get("config_id") or line.dograh_config_id
    line.dograh_phone_number_id = saved.get("phone_number_id") or line.dograh_phone_number_id
    line.save(update_fields=["dograh_config_id", "dograh_phone_number_id", "updated_at"])
    return line

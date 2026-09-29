"""WhatsApp Cloud API calling: enable SIP and ask the customer for permission."""

import httpx
from django.conf import settings

GRAPH = "https://graph.facebook.com/v21.0"


def _headers(connection):
    return {"Authorization": f"Bearer {connection.access_token}"}


def enable_calling(connection, calling):
    if not connection.phone_number_id or not connection.access_token:
        raise RuntimeError("WhatsApp connection is incomplete")
    payload = {
        "calling": {
            "status": "ENABLED",
            "sip": {
                "status": "ENABLED",
                "servers": [{"hostname": settings.SIP_HOSTNAME, "port": 5061}],
            },
        }
    }
    response = httpx.post(
        f"{GRAPH}/{connection.phone_number_id}/settings",
        json=payload,
        headers=_headers(connection),
        timeout=20.0,
    )
    response.raise_for_status()
    calling.calling_enabled = True
    calling.sip_enabled = True
    calling.save(update_fields=["calling_enabled", "sip_enabled", "updated_at"])
    return response.json()


def fetch_sip_password(connection, calling):
    response = httpx.get(
        f"{GRAPH}/{connection.phone_number_id}/settings",
        params={"include_sip_credentials": "true"},
        headers=_headers(connection),
        timeout=20.0,
    )
    response.raise_for_status()
    body = response.json()
    calling_block = body.get("calling") or body
    servers = ((calling_block.get("sip") or {}).get("servers")) or []
    password = ""
    if servers:
        password = servers[0].get("password") or servers[0].get("sip_password") or ""
    if not password:
        raise RuntimeError("Meta did not return a SIP password")
    calling.sip_password = password
    calling.save(update_fields=["sip_password", "updated_at"])
    return password


def send_call_permission_request(connection, to_e164, body):
    response = httpx.post(
        f"{GRAPH}/{connection.phone_number_id}/messages",
        json={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_e164.lstrip("+"),
            "type": "interactive",
            "interactive": {
                "type": "call_permission_request",
                "action": {"name": "call_permission_request"},
                "body": {"text": body[:1024]},
            },
        },
        headers=_headers(connection),
        timeout=20.0,
    )
    response.raise_for_status()
    return response.json()

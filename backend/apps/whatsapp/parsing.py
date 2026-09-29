"""Pull a message out of a WhatsApp Cloud API webhook body."""


def iter_messages(payload):
    if not isinstance(payload, dict):
        return
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            contacts = value.get("contacts") or []
            name = ""
            if contacts:
                name = ((contacts[0].get("profile") or {}).get("name")) or ""
            for message in value.get("messages") or []:
                parsed = parse_message(message, name)
                if parsed:
                    yield parsed


def parse_message(message, contact_name=""):
    if not isinstance(message, dict) or not message.get("id"):
        return None
    kind = message.get("type")
    body = ""
    button_payload = ""
    if kind == "text":
        body = ((message.get("text") or {}).get("body")) or ""
    elif kind == "button":
        button = message.get("button") or {}
        body = button.get("text") or ""
        button_payload = button.get("payload") or ""
    elif kind == "interactive":
        interactive = message.get("interactive") or {}
        if interactive.get("type") == "call_permission_reply":
            reply = interactive.get("call_permission_reply") or {}
            return {
                "wa_message_id": message["id"],
                "from": str(message.get("from") or ""),
                "body": "",
                "button_payload": "",
                "context_id": str((message.get("context") or {}).get("id") or "").strip(),
                "contact_name": contact_name.strip(),
                "kind": "call_permission_reply",
                "permission_response": str(reply.get("response") or "").lower(),
                "permission_permanent": bool(reply.get("is_permanent")),
                "permission_expires": reply.get("expiration_timestamp"),
            }
        reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
        body = reply.get("title") or ""
        button_payload = reply.get("id") or ""
    else:
        return None
    context = message.get("context") or {}
    return {
        "wa_message_id": message["id"],
        "from": str(message.get("from") or ""),
        "body": body.strip(),
        "button_payload": str(button_payload).strip(),
        "context_id": str(context.get("id") or "").strip(),
        "contact_name": contact_name.strip(),
        "kind": kind or "message",
    }

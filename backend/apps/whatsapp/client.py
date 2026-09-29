import httpx


def send_text(connection, to_e164, body):
    if not connection.phone_number_id or not connection.access_token:
        raise RuntimeError("WhatsApp connection is incomplete")
    url = f"https://graph.facebook.com/v21.0/{connection.phone_number_id}/messages"
    response = httpx.post(
        url,
        json={
            "messaging_product": "whatsapp",
            "to": to_e164.lstrip("+"),
            "type": "text",
            "text": {"body": body},
        },
        headers={"Authorization": f"Bearer {connection.access_token}"},
        timeout=15.0,
    )
    response.raise_for_status()
    return response.json()

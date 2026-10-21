"""Put the phone provider's call id on an inbound Dograh run.

The booking agent remembers a call by this id. Copy onto a new dograh-api
container with:

    docker cp deploy/dograh-overrides/apply_inbound_context.py dograh-api:/tmp/apply_inbound_context.py
    docker exec dograh-api python /tmp/apply_inbound_context.py
    docker restart dograh-api
"""

from pathlib import Path

path = Path("/app/api/routes/telephony.py")
text = path.read_text()
old = """        initial_context={
            "caller_number": normalized_data.from_number,
            "called_number": normalized_data.to_number,
            "direction": "inbound",
            "provider": provider,
            "telephony_configuration_id": telephony_configuration_id,
        },"""
new = """        initial_context={
            "caller_number": normalized_data.from_number,
            "called_number": normalized_data.to_number,
            "direction": "inbound",
            "provider": provider,
            "provider_call_id": call_id,
            "telephony_configuration_id": telephony_configuration_id,
        },"""
if new in text:
    print("already patched")
elif old not in text:
    raise SystemExit("inbound context block was not found")
else:
    path.write_text(text.replace(old, new, 1))
    print("patched")

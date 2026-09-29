"""Node fields Dograh accepts, taken from the pinned checkout's typed SDK.

Unknown keys are rejected so a prompt or greeting cannot be smuggled into a
field Dograh would treat as instructions.
"""

ALLOWED = {
    "startCall": {
        "name",
        "prompt",
        "greeting",
        "greeting_type",
        "allow_interrupt",
        "add_global_prompt",
    },
    "agentNode": {"name", "prompt", "allow_interrupt", "add_global_prompt"},
    "endCall": {"name", "prompt", "add_global_prompt"},
    "webhook": {
        "name",
        "enabled",
        "http_method",
        "endpoint_url",
        "custom_headers",
        "payload_template",
    },
}


def check_definition(definition):
    nodes = definition.get("nodes") or []
    starts = [node for node in nodes if node.get("type") == "startCall"]
    if len(starts) != 1:
        raise ValueError("A workflow must contain exactly one startCall node")
    for node in nodes:
        kind = node.get("type")
        if kind not in ALLOWED:
            raise ValueError(f"Unsupported node type {kind}")
        data = node.get("data") or {}
        unknown = set(data) - ALLOWED[kind]
        if unknown:
            raise ValueError(f"{kind} has unknown fields: {', '.join(sorted(unknown))}")
        if kind in {"startCall", "agentNode", "endCall"} and not str(data.get("prompt") or "").strip():
            raise ValueError(f"{kind} needs a prompt")

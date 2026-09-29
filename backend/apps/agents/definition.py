from apps.agents.node_spec import check_definition
from apps.campaigns.prompt_compiler import MINIMAL_DOGRAH_PROMPT


def build_workflow_definition(profile, *, webhook_url, webhook_token):
    greeting = (profile.greeting or "").strip()
    closing = (profile.closing_line or "").strip()
    definition = {
        "nodes": [
            {
                "id": "1",
                "type": "startCall",
                "position": {"x": 0, "y": 0},
                "data": {
                    "name": "Start",
                    "prompt": "Speak the greeting, then wait. Do not add offers or prices.",
                    "greeting": greeting,
                    "greeting_type": "text",
                    "allow_interrupt": profile.allow_interrupt,
                    "add_global_prompt": False,
                },
            },
            {
                "id": "2",
                "type": "agentNode",
                "position": {"x": 280, "y": 0},
                "data": {
                    "name": "Conversation",
                    "prompt": MINIMAL_DOGRAH_PROMPT,
                    "allow_interrupt": profile.allow_interrupt,
                    "add_global_prompt": False,
                },
            },
            {
                "id": "3",
                "type": "endCall",
                "position": {"x": 560, "y": 0},
                "data": {
                    "name": "Close",
                    "prompt": closing,
                    "add_global_prompt": False,
                },
            },
            {
                "id": "4",
                "type": "webhook",
                "position": {"x": 840, "y": 0},
                "data": {
                    "name": "Status",
                    "enabled": True,
                    "http_method": "POST",
                    "endpoint_url": webhook_url,
                    "custom_headers": [{"key": "X-Dograh-Token", "value": webhook_token}],
                    "payload_template": {
                        "run_id": "{{workflow_run_id}}",
                        "status": "completed",
                        "transcript_url": "{{transcript_url}}",
                        "recording_url": "{{recording_url}}",
                        "initial_context": "{{initial_context}}",
                    },
                },
            },
        ],
        "edges": [
            {
                "id": "1-2",
                "source": "1",
                "target": "2",
                "data": {"label": "continue", "condition": "The greeting is finished."},
            },
            {
                "id": "2-3",
                "source": "2",
                "target": "3",
                "data": {
                    "label": "done",
                    "condition": "The caller is finished, asked for a person, or the goal is complete.",
                },
            },
            {
                "id": "3-4",
                "source": "3",
                "target": "4",
                "data": {"label": "report", "condition": "The call is ending."},
            },
        ],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }
    check_definition(definition)
    agent_prompt = next(node["data"]["prompt"] for node in definition["nodes"] if node["type"] == "agentNode")
    if agent_prompt != MINIMAL_DOGRAH_PROMPT:
        raise ValueError("The agent node must use only the minimal template")
    return definition

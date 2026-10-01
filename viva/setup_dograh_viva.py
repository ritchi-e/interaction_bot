"""Create a Dograh account and two viva agents: one English, one Hindi.

Both agents share one org-level model configuration (OpenAI LLM, Deepgram
STT, Rumik through context_guard/rumik_bridge.py on port 8090). Each workflow
then overrides just the STT language and the TTS voice preset it needs:

- English: Deepgram STT pinned to "en" (a dedicated single-language model is
  more accurate than "multi" for audio that is not actually code-switched),
  Rumik voice preset "rumik-siya-english-indian".
- Hindi: Deepgram STT stays on "multi" — Deepgram's own guidance is to keep
  multilingual code-switching on for Hindi speech that mixes in English
  words (Hinglish), which is what real candidates do — plus a Deepgram
  keyterm list of the domain words that were misheard in testing (Dograh,
  Rumik, latency, API, ...). Rumik voice preset "rumik-siya-hindi". The
  prompt also tells the model to always use feminine Hindi verb forms, since
  the voice is a woman and the model has no other way to know that.

This file lives outside the product app on purpose. Run it from the repo root
after the local Dograh stack is up:

    python viva/setup_dograh_viva.py [--config-only]
"""

import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
API = os.environ.get("DOGRAH_LOCAL_API", "http://127.0.0.1:8010/api/v1")
EMAIL = "viva@phonwa.online"
PASSWORD = "supersecret1"

# Domain words that Deepgram mis-transcribed in testing (e.g. "वायवाह" for
# "viva one", "latency company" for "latency ko"). Keyterm Prompting biases
# Deepgram toward these regardless of language.
KEYTERMS = "Dograh, Rumik, Deepgram, Sarvam, latency, API, orchestrator, viva"

ENGLISH_PROMPT = (
    "You are conducting a short viva. Always reply in English, even if the "
    "candidate answers in Hindi or Hinglish. Ask one question at a time: "
    "their name if you do not have it, then one question about a recent "
    "project, then one follow-up. Keep every turn to one or two short "
    "sentences. Do not invent scores or prices."
)
HINDI_PROMPT = (
    "You are conducting a short viva. Always reply in Hindi, written in "
    "Devanagari, even if the candidate answers in English or Hinglish. You "
    "are a woman: always use feminine Hindi verb forms for yourself (जैसे "
    "'समझ गई', 'पूछूँगी', 'बताऊँगी'), never masculine forms ('समझ गया', "
    "'पूछूँगा'). The candidate will likely mix in English technical words "
    "(API, latency, orchestrator) inside Hindi sentences — that is normal, "
    "just respond in Hindi. Ask one question at a time: their name if you do "
    "not have it, then one question about a recent project, then one "
    "follow-up. Keep every turn to one or two short sentences. Do not invent "
    "scores or prices."
)

WORKFLOWS = {
    "english": {
        "name": "Viva practice — English",
        "greeting": (
            "Hello. This is a short practice viva. Tell me your name, then I "
            "will ask you one question."
        ),
        "prompt": ENGLISH_PROMPT,
        "model_overrides": {
            "stt": {"provider": "deepgram", "language": "en"},
            "tts": {"provider": "openai", "model": "rumik-siya-english-indian"},
        },
    },
    "hindi": {
        "name": "Viva practice — Hindi",
        "greeting": (
            "नमस्ते। यह एक छोटा अभ्यास विवा है। अपना नाम बताइए, उसके बाद मैं एक "
            "सवाल पूछूँगी।"
        ),
        "prompt": HINDI_PROMPT,
        "model_overrides": {
            "stt": {"provider": "deepgram", "language": "multi"},
            "tts": {"provider": "openai", "model": "rumik-siya-hindi"},
        },
    },
}


def load_env():
    for line in (ROOT / ".env").read_text().splitlines():
        if not line.strip() or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    if not os.environ.get("DEEPGRAM_API_KEY"):
        os.environ["DEEPGRAM_API_KEY"] = os.environ.get("deepgram_nova3_api", "")


def base_model_config():
    return {
        "version": 2,
        "mode": "byok",
        "byok": {
            "mode": "pipeline",
            "pipeline": {
                "llm": {
                    "provider": "openai",
                    "model": os.environ.get("UPSTREAM_LLM_MODEL", "gpt-4o-mini"),
                    "api_key": os.environ["UPSTREAM_LLM_API_KEY"],
                    "base_url": "https://api.openai.com/v1",
                },
                "stt": {
                    "provider": "deepgram",
                    "model": "nova-3",
                    "language": "multi",
                    "api_key": os.environ["DEEPGRAM_API_KEY"],
                },
                "tts": {
                    "provider": "openai",
                    "model": "gpt-4o-mini-tts",
                    "voice": "alloy",
                    "api_key": os.environ["RUMIK_API_KEY"],
                    "base_url": os.environ.get(
                        "RUMIK_BRIDGE_URL", "http://host.docker.internal:8090/v1"
                    ),
                },
                "embeddings": {
                    "provider": "openai",
                    "model": "text-embedding-3-small",
                    "api_key": os.environ["UPSTREAM_LLM_API_KEY"],
                },
            },
        },
    }


def upsert_workflow(client, headers, key, spec, existing_by_name):
    existing = existing_by_name.get(spec["name"])
    if existing is None:
        created = client.post(
            f"{API}/workflow/create/definition",
            headers=headers,
            json={
                "name": spec["name"],
                "workflow_definition": {
                    "nodes": [
                        {
                            "id": "1",
                            "type": "startCall",
                            "position": {"x": 0, "y": 0},
                            "data": {
                                "name": "Greet",
                                "greeting_type": "text",
                                "greeting": spec["greeting"],
                                "prompt": spec["prompt"],
                                "allow_interrupt": True,
                                "add_global_prompt": False,
                            },
                        }
                    ],
                    "edges": [],
                    "viewport": {"x": 0, "y": 0, "zoom": 1},
                },
            },
        )
        if created.status_code >= 400:
            raise SystemExit(f"create {key} {created.status_code}: {created.text[:500]}")
        workflow_id = created.json().get("id")
    else:
        workflow_id = existing["id"]
        current = client.get(f"{API}/workflow/fetch/{workflow_id}", headers=headers)
        current.raise_for_status()
        definition = current.json()["workflow_definition"]
        node = definition["nodes"][0]["data"]
        node["greeting"] = spec["greeting"]
        node["prompt"] = spec["prompt"]
        updated = client.put(
            f"{API}/workflow/{workflow_id}",
            headers=headers,
            json={"name": spec["name"], "workflow_definition": definition},
        )
        if updated.status_code >= 400:
            raise SystemExit(f"update {key} definition {updated.status_code}: {updated.text[:500]}")

    configured = client.put(
        f"{API}/workflow/{workflow_id}",
        headers=headers,
        json={
            "workflow_configurations": {
                "model_overrides": spec["model_overrides"],
                "dictionary": KEYTERMS,
            }
        },
    )
    if configured.status_code >= 400:
        raise SystemExit(f"configure {key} {configured.status_code}: {configured.text[:500]}")

    published = client.post(f"{API}/workflow/{workflow_id}/publish", headers=headers)
    if published.status_code >= 400:
        raise SystemExit(f"publish {key} {published.status_code}: {published.text[:500]}")

    return workflow_id


def main():
    load_env()
    with httpx.Client(timeout=60.0) as client:
        signup = client.post(
            f"{API}/auth/signup",
            json={"email": EMAIL, "password": PASSWORD, "name": "Viva"},
        )
        if signup.status_code == 409:
            signup = client.post(
                f"{API}/auth/login",
                json={"email": EMAIL, "password": PASSWORD},
            )
        signup.raise_for_status()
        token = signup.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        config = base_model_config()
        saved = client.put(
            f"{API}/organizations/model-configurations/v2", headers=headers, json=config
        )
        if saved.status_code >= 400:
            raise SystemExit(f"model config {saved.status_code}: {saved.text[:500]}")
        if "--config-only" in sys.argv:
            print(json.dumps({"email": EMAIL, "tts": config["byok"]["pipeline"]["tts"]["base_url"]}))
            return

        listing = client.get(f"{API}/workflow/fetch", headers=headers)
        listing.raise_for_status()
        existing_by_name = {w["name"]: w for w in listing.json()}
        # The one pre-existing "Viva practice" workflow becomes the English one,
        # so its run history and workflow id are kept instead of orphaned.
        if "Viva practice" in existing_by_name and WORKFLOWS["english"]["name"] not in existing_by_name:
            existing_by_name[WORKFLOWS["english"]["name"]] = existing_by_name["Viva practice"]

        out = {"email": EMAIL, "workflows": {}}
        for key, spec in WORKFLOWS.items():
            workflow_id = upsert_workflow(client, headers, key, spec, existing_by_name)
            out["workflows"][key] = {
                "workflow_id": workflow_id,
                "url": f"http://127.0.0.1:3010/workflow/{workflow_id}?onboarding=web_call",
            }
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

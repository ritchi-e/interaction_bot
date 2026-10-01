# Dograh provider notes

Dograh's OpenAI LLM provider accepts a custom base URL. Point it at the context guard. The guard calls the hosted model (OpenAI by default). Do not put the OpenAI key in Dograh.

| Setting | Value |
| --- | --- |
| LLM provider | OpenAI (compatible) |
| Base URL | `http://context-guard:8080/v1` |
| Model | `gpt-4o-mini` (or whatever `UPSTREAM_LLM_MODEL` is set to) |
| Transcriber | Deepgram Nova-3, language `multi` (a campaign overrides this to `hi`/`en`/`multi` to match its own language) |
| Voice | Rumik, through the Rumik bridge. The campaign language picks the voice (`rumik-siya-hindi`, `rumik-siya-english-indian`, or `rumik-siya-hinglish`) |
| Telephony | Plivo. A WhatsApp reply starts the campaign; Dograh dials the mobile through Plivo |

Run `python manage.py bootstrap_dograh` (from `backend/`) to PUT this base configuration once instead of pasting it into Dograh's UI by hand. Every business shares the same Dograh org (one platform API key), so this only needs to run once per environment, and again whenever the base defaults themselves change.

The agent node prompt must stay the minimal template from `MINIMAL_DOGRAH_PROMPT` in `backend/apps/campaigns/prompt_compiler.py`. The dashboard's "Preview prompt" button prints it. The context guard deletes any other system prompt and inserts the campaign's facts.

## Per-campaign STT language and TTS voice

Each `Campaign` has its own `language` (`hi` / `en_in` / `hinglish`). `backend/apps/agents/model_overrides.py` turns that into a `workflow_configurations.model_overrides` payload that `apps/agents/publish.py` sends every time an agent is published — on top of the shared base above, not replacing it. Speech-to-text always gets an explicit language override (`hi`, `en`, or `multi`). The voice is Rumik, chosen from that same language. Businesses do not pick a provider or paste keys.

No keyterm dictionary is set here. That mechanism lives only in the local viva tester (`viva/setup_dograh_viva.py`), whose calls are about a fixed technical vocabulary. Real campaigns talk about a business's own offer, so there's nothing worth biasing every call toward.

## Rumik

Rumik is not a Dograh-native TTS provider, so it's fronted by `rumik-bridge`, an OpenAI-compatible facade (`context_guard/rumik_bridge.py`, deployed as its own service in `deploy/docker-compose.yml`) with Rumik's low-latency streaming voice behind it. A campaign that picks Rumik gets a TTS override shaped like OpenAI's provider (`provider: "openai"`, `base_url` pointing at `rumik-bridge`), with the voice selected through the `model` field — Dograh's OpenAI TTS client only accepts a fixed set of OpenAI voice names in `voice`, but passes `model` straight through, so that's where a Rumik speaker + language preset travels. See the presets in `rumik_bridge.py` and `apps/agents/model_overrides.py::rumik_voice_model_for`.

This supersedes the older plan (copying a patched TTS service into the Dograh image by hand); the bridge needs no changes inside Dograh at all.

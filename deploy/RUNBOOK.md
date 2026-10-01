# Deploying

One machine, with a public IP. No GPU. Speech-to-text is Deepgram, the voice is a hosted provider (Sarvam by default), and the language model is a hosted API (OpenAI `gpt-4o-mini` by default). The context guard sits in front of that API so the agent cannot leave the campaign.

```text
Internet
  |  443 (dashboard and webhooks)
  v
App VM
  Caddy, Django, Celery, Postgres, Redis, Next.js
  Plivo  (outbound phone calls)
  context guard  (private, calls OpenAI)
  rumik-bridge   (private, OpenAI-compatible facade over Rumik's streaming TTS)
  Dograh (its own compose, joined to the Docker network named "caller")
        |
        +--> Deepgram, Sarvam, Rumik (via rumik-bridge), OpenAI
        +--> Plivo, WhatsApp messages
```

`/internal/` on Django is not published by Caddy. The context guard calls Django at `http://backend:8000` on the Docker network.

## 1. App machine

```bash
cp .env.example .env
```

Replace `DJANGO_SECRET_KEY`, `FERNET_KEY`, `INTERNAL_API_TOKEN`, and `DOGRAH_WEBHOOK_SECRET`. Generate the first two with:

```bash
python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

Set `UPSTREAM_LLM_API_KEY` to your OpenAI key. To use another OpenAI-compatible host, also set `UPSTREAM_LLM_BASE_URL` and `UPSTREAM_LLM_MODEL`. Set `DEEPGRAM_API_KEY` and `SARVAM_API_KEY`. Point `APP_DOMAIN` at the hostname that has an A record to this machine.

```bash
docker compose -f deploy/docker-compose.yml up --build -d
```

Caddy fetches a certificate for `APP_DOMAIN`.

## 2. Dograh and Plivo

From the Dograh checkout (`./scripts/fetch_dograh.sh`):

```bash
docker compose -f docker-compose.yaml -f ../AI_Caller/deploy/dograh.override.yml up -d
```

The override puts Dograh on the `caller` network. Run the base model configuration once instead of pasting JSON into Dograh's UI:

```bash
docker compose -f deploy/docker-compose.yml exec backend python manage.py bootstrap_dograh
```

This sets the language model to OpenAI-compatible with base URL `http://context-guard:8080/v1` and model `gpt-4o-mini`, speech-to-text to Deepgram Nova-3 (language `multi`), and voice to Sarvam Bulbul — the shared base every business's workflow starts from, since they all use the one platform Dograh API key. See `deploy/dograh-overrides/README.md`.

Businesses publish the agent from the campaign page. The published workflow carries the greeting, the minimal prompt, a webhook to `https://APP_DOMAIN/webhooks/dograh/<slug>/` with header `X-Dograh-Token`, and per-campaign `workflow_configurations.model_overrides` — Deepgram STT pinned to the campaign's own language (`hi`/`en`/`multi`), and, if the campaign picked a TTS provider other than the shared default, a self-contained override for it (Rumik goes through the `rumik-bridge` service for low-latency streaming; see `apps/agents/model_overrides.py`). Role and persona stay in the context guard prompt, not in Dograh.

Calls go out through Plivo. In Setup, Calling, save the Plivo Auth ID, Auth Token, and the caller ID. That writes a Plivo telephony configuration into Dograh and registers the caller ID. A WhatsApp reply is the customer's consent to be called. The agent then dials that mobile through Plivo, only between 09:00 and 21:00 IST. `STOP` opts the number out. The limit is 5 calls per person in 24 hours.

## 3. WhatsApp

In Meta, the callback URL is:

```text
https://APP_DOMAIN/webhooks/whatsapp/<business-slug>/
```

The verify token is generated when the business signs up and is shown on the Setup page. Subscribe to the `messages` field.

When the business sends a template, record the outbound message id so a reply can be matched to the campaign:

```text
POST /api/campaigns/<id>/outbound-messages/
{"wa_message_id": "wamid....", "phone": "+9198..."}
```

A reply button can also carry the payload `campaign:<campaign uuid>`. Otherwise a keyword, then the default campaign, is used.

## 4. What the agent is allowed to say

Campaign context is structured: offer, prices, FAQs, allowed topics, forbidden topics, competitors, and the handoff sentence. The context guard replaces Dograh's system prompt with the compiled one on every turn, forces temperature 0.2, and checks each sentence before it is returned. A sentence is replaced with the handoff line when it contains a number that is not in the facts, a forbidden topic, a competitor, or a script other than Devanagari or Latin. The red-team tests in `context_guard/tests/test_redteam.py` fail the build if that check regresses.

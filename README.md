# Caller

When someone replies to a WhatsApp campaign, Caller places an outbound voice call and talks about that campaign. The agent speaks Hindi or Indian English, and it is only allowed to say the offer, prices, and answers the business entered.

Dograh places the call through WhatsApp. After a reply, the customer is asked for permission, and the agent rings them on WhatsApp only if they tap Allow. Deepgram transcribes. A hosted voice (Sarvam by default) speaks. The language model is a hosted API (GPT-4o-mini by default). Every reply passes through a proxy that drops anything outside the campaign.

Fetch Dograh beside this app with `./scripts/fetch_dograh.sh` (pinned release `dograh-v1.47.0`).

## Run it locally

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt -r context_guard/requirements.txt
cd backend && ../.venv/bin/python manage.py migrate && ../.venv/bin/python manage.py runserver
```

In another terminal:

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:3000, create a business, then a campaign. "Preview prompt" shows the text to paste into the Dograh agent node, and the locked prompt the caller never sees.

The context guard, when you are ready to talk to a model:

```bash
cd context_guard
UPSTREAM_LLM_BASE_URL=https://api.openai.com/v1 \
UPSTREAM_LLM_API_KEY=sk-... \
UPSTREAM_LLM_MODEL=gpt-4o-mini \
BACKEND_INTERNAL_URL=http://127.0.0.1:8000 \
INTERNAL_API_TOKEN=test-internal \
../.venv/bin/uvicorn server:app --port 8080
```

Another OpenAI-compatible host works the same way. Change the base URL, key, and model name.

Tests:

```bash
cd backend && ../.venv/bin/pytest
cd context_guard && ../.venv/bin/pytest
```

## Deploy

See [deploy/RUNBOOK.md](deploy/RUNBOOK.md). One machine, no GPU:

```bash
docker compose -f deploy/docker-compose.yml up --build
```

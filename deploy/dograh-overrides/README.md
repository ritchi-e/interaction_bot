# Dograh provider notes

Dograh's OpenAI LLM provider accepts a custom base URL. Point it at the context guard. The guard calls the hosted model (OpenAI by default). Do not put the OpenAI key in Dograh.

| Setting | Value |
| --- | --- |
| LLM provider | OpenAI (compatible) |
| Base URL | `http://context-guard:8080/v1` |
| Model | `gpt-4o-mini` (or whatever `UPSTREAM_LLM_MODEL` is set to) |
| Transcriber | Deepgram Nova-3, language `multi`, endpointing 300ms |
| Voice | Sarvam Bulbul (`bulbul:v2`, voice `anushka`) unless the campaign picks Cartesia or ElevenLabs |
| Telephony | WhatsApp, via the Asterisk bridge (`PJSIP/+91…@endpoint`) |

The agent node prompt must stay the minimal template from `MINIMAL_DOGRAH_PROMPT` in `backend/apps/campaigns/prompt_compiler.py`. The dashboard's "Preview prompt" button prints it. The context guard deletes any other system prompt and inserts the campaign's facts.

## Rumik

`rumik_tts.py` is the adapter for campaigns whose voice is Rumik. Dograh has no built-in Rumik provider.

1. Copy `rumik_tts.py` into the Dograh API image.
2. In the voice branch of the service factory, when the configured provider is `rumik`, return `build_rumik_tts(api_key=..., voice=...)`.
3. Set `RUMIK_API_URL` to Rumik's streaming speech endpoint.

Until that URL is confirmed for your account, leave campaigns on Sarvam.

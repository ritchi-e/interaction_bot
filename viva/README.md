# Viva tester

A local Dograh practice call. It does not phone anyone, it does not use WhatsApp, and it is not part of the product app.

From the Dograh checkout, with this repo's caller network already up:

```bash
docker compose -f docker-compose.yaml -f ../AI_Caller/viva/dograh.local.yml up -d
```

The Rumik bridge for this tester listens on port 8090 on the host:

```bash
cd viva
uvicorn rumik_bridge:app --host 0.0.0.0 --port 8090
```

(`RUMIK_API_KEY` must be set in the environment.) Then, from the repo root:

```bash
python viva/setup_dograh_viva.py
```

Sign in at http://127.0.0.1:3010 as `viva@phonwa.online` / `supersecret1`.

- English: http://127.0.0.1:3010/workflow/1?onboarding=web_call
- Hindi: http://127.0.0.1:3010/workflow/2?onboarding=web_call

Both use Rumik's Siya voice for the viva tester only. Production campaigns on the `selfhost` branch use self-hosted speech-stt / speech-tts instead.

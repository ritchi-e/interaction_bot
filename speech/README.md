# Self-hosted speech

GPU services used by Dograh on the `selfhost` branch:

| Service | Protocol | Model |
|---------|----------|--------|
| `speech-stt` | Deepgram Flux WebSocket `/v2/listen` | Nemotron (sherpa-onnx) + Silero VAD + smart-turn |
| `speech-tts` | OpenAI `/v1/audio/speech` + `/v1/audio/prewarm` | dheeyantra/dhee-indic-f5 |

Campaign languages are **Hindi** and **Indian English** only. Hindi STT/TTS already handle English loanwords (code-switching).

TTS exposes four **system voices**: Hindi/English × Female/Male. Users pick
Female or Male in the campaign UI. Reference clips live in
`speech/data_for_voice/` (source) and `speech/tts/voices/` (runtime; also
copied into `/models/tts/voices` by the speech-models job).

There is no separate “train/clone” step. The same four fixed wav+txt pairs are
reused on every request as the speaker condition; identical phrases are also
cached as PCM so greetings are free after the first synthesis.

See [deploy/RUNBOOK.md](../deploy/RUNBOOK.md) for GPU setup, model fetch, and rollout.

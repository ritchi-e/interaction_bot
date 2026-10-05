# GPU server setup (Cursor agent runbook)

Use this on the **Ubuntu GPU EC2** after DNS A records already point at the machine’s public IP. Goal: clone the app, put **Postgres, TLS certs, and speech models** on the **100GB EBS** volume so they survive stop/start, then bring up Caller + self-hosted STT/TTS + Dograh.

**Branch:** `selfhost`  
**Repo:** `https://github.com/ritchi-e/interaction_bot.git`

---

## 0. Assumptions and paths

| Item | Value |
|------|--------|
| EBS mount | `/data` (100GB, xfs or ext4) |
| App data root | `/data/caller` (Postgres, models, Caddy ACME) |
| App clone | `/data/caller/interaction_bot` (recommended) |
| Compose | Always run from repo root with **two** files: `deploy/docker-compose.yml` + `deploy/docker-compose.data.yml` |

Set once in the shell profile or before every compose command:

```bash
export CALLER_DATA_ROOT=/data/caller
export COMPOSE_FILES="-f deploy/docker-compose.yml -f deploy/docker-compose.data.yml"
```

Helper alias (optional):

```bash
dc() { docker compose $COMPOSE_FILES "$@"; }
```

---

## 1. Mount the 100GB EBS (if not already)

Identify the volume (example: `/dev/nvme1n1` — **verify with `lsblk`**, not by guessing):

```bash
lsblk -f
sudo file -s /dev/nvme*n1   # look for "data" vs empty
```

Format **only** if the disk has no filesystem:

```bash
sudo mkfs.ext4 -L caller-data /dev/nvme1n1   # replace device
```

Mount and persist:

```bash
sudo mkdir -p /data
sudo mount /dev/nvme1n1 /data   # replace device
UUID=$(sudo blkid -s UUID -o value /dev/nvme1n1)
echo "UUID=$UUID /data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
sudo chown ubuntu:ubuntu /data
```

Create persistent directories:

```bash
mkdir -p /data/caller/{pgdata,caddy-data,speech-models,interaction_bot}
chmod 700 /data/caller/pgdata
```

---

## 2. Host prerequisites

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates python3-pip

# NVIDIA driver (if nvidia-smi missing, install AWS/Ubuntu GPU driver package for your AMI)
nvidia-smi

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
# log out/in or: newgrp docker

# NVIDIA Container Toolkit
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

**Security group (AWS):** allow **22** from your admin IP, **80** and **443** from `0.0.0.0/0` (Caddy + Let’s Encrypt). Dograh UI port (often **3010**) only if you need browser access to Dograh directly.

---

## 3. Clone the application

```bash
cd /data/caller
git clone --branch selfhost --depth 1 https://github.com/ritchi-e/interaction_bot.git interaction_bot
cd interaction_bot
./scripts/fetch_dograh.sh
```

Dograh lands in `./dograh/` (pinned `dograh-v1.47.0`).

---

## 4. Configure `.env`

```bash
cp .env.example .env
nano .env   # or vim
```

Generate secrets:

```bash
python3 -c "import base64,os; print('DJANGO_SECRET_KEY=', base64.urlsafe_b64encode(os.urandom(32)).decode())"
python3 -c "import base64,os; print('FERNET_KEY=', base64.urlsafe_b64encode(os.urandom(32)).decode())"
python3 -c "import secrets; print('INTERNAL_API_TOKEN=', secrets.token_urlsafe(32))"
python3 -c "import secrets; print('DOGRAH_WEBHOOK_SECRET=', secrets.token_urlsafe(32))"
python3 -c "import secrets; print('SPEECH_API_TOKEN=', secrets.token_urlsafe(32))"
```

**Required / important variables:**

| Variable | Notes |
|----------|--------|
| `APP_DOMAIN` | Public hostname (DNS already set), e.g. `phonwa.online` |
| `ACME_EMAIL` | Email for Let’s Encrypt |
| `DJANGO_ALLOWED_HOSTS` | Include `APP_DOMAIN`, `www.`, `backend` |
| `PUBLIC_BASE_URL` | `https://APP_DOMAIN` |
| `NEXT_PUBLIC_API_URL` | Leave empty in compose build (Caddy same-origin) or set if needed |
| `UPSTREAM_LLM_API_KEY` | OpenAI or compatible (Gemini OpenAI bridge, etc.) |
| `UPSTREAM_LLM_BASE_URL` / `UPSTREAM_LLM_MODEL` | Default OpenAI `gpt-4o-mini` |
| `DOGRAH_API_URL` | After Dograh is up: usually `http://dograh-api:8000` on Docker network — see step 6 |
| `DOGRAH_API_KEY` | From Dograh org/API after first Dograh login |
| `HF_TOKEN` | Optional; faster HF downloads. `dhee-indic-f5` is public |
| `SPEECH_API_TOKEN` | Same value Dograh/bootstrap will send to STT/TTS |
| `POSTGRES_PASSWORD` | Set a strong password; matches compose default override |

Keep `SPEECH_STT_URL` / `SPEECH_TTS_URL` at defaults for in-cluster URLs.

---

## 5. Download speech models (into EBS)

First run can take **20–60+ minutes** (Nemotron fallback tarball + ~1.4GB TTS + smart-turn). Models go to `/data/caller/speech-models` via the data compose file.

```bash
export CALLER_DATA_ROOT=/data/caller
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.data.yml \
  --profile models run --rm speech-models
```

Verify:

```bash
du -sh /data/caller/speech-models
ls /data/caller/speech-models/stt/nemotron/*.onnx 2>/dev/null | head
ls /data/caller/speech-models/tts/dhee-indic-f5/model.safetensors 2>/dev/null
ls /data/caller/speech-models/tts/voices/
```

Re-run the same `speech-models` command after wiping that directory or changing model IDs.

---

## 6. Start Caller stack (GPU STT/TTS + app)

```bash
export CALLER_DATA_ROOT=/data/caller
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.data.yml up --build -d
```

Watch GPU services (TTS warmup can take **several minutes**):

```bash
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.data.yml ps
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.data.yml logs -f speech-tts speech-stt
nvidia-smi
```

Health checks:

```bash
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.data.yml exec speech-stt \
  python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read())"
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.data.yml exec speech-tts \
  python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read())"
curl -sI "https://${APP_DOMAIN}/" | head
```

Backend runs `migrate` on container start automatically.

---

## 7. Start Dograh on the `caller` network

The **caller** network must exist (created by step 6).

From repo root:

```bash
cd dograh
```

Follow Dograh’s OSS Docker docs to generate its `.env` (see `dograh/scripts/start_docker.sh` or upstream README). Typical pattern:

- Copy their env template, set DB/redis secrets, set `DEPLOYMENT_MODE=oss`.
- Start with the override that attaches Dograh API/UI to network `caller`:

```bash
docker compose -f docker-compose.yaml -f ../deploy/dograh.override.yml up -d
cd ..
```

Obtain **DOGRAH_API_KEY** from the Dograh UI or API (org settings). Put it in `/data/caller/interaction_bot/.env`:

```bash
DOGRAH_API_URL=http://dograh-api:8000
DOGRAH_API_KEY=<from Dograh>
```

Recreate backend so it picks up the key:

```bash
export CALLER_DATA_ROOT=/data/caller
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.data.yml up -d backend celery
```

Wire Dograh to self-hosted speech + context guard:

```bash
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.data.yml \
  exec backend python manage.py bootstrap_dograh
```

Expected: LLM → `context-guard`, STT → `speech-stt`, TTS → `speech-tts`.

**Republish** each campaign agent in the dashboard so per-campaign STT language and TTS voice overrides apply.

---

## 8. Post-setup checks

```bash
# Optional bench (install deps on host)
pip3 install httpx websockets
SPEECH_STT_URL=http://127.0.0.1:8000 SPEECH_TTS_URL=http://127.0.0.1:8000/v1 \
  python3 speech/bench/bench.py --concurrency 1 4
```

Targets (tune later): STT EndOfTurn p50 ≤ 450ms; TTS first audio p50 ≤ 250ms.

Plivo + WhatsApp: see [RUNBOOK.md](./RUNBOOK.md) sections 2–3.

---

## 9. Operations cheat sheet

| Task | Command |
|------|---------|
| Restart stack | `dc up -d` (with `COMPOSE_FILES` / `CALLER_DATA_ROOT` set) |
| Logs | `dc logs -f backend speech-stt speech-tts context-guard` |
| Update code | `git pull && dc up --build -d` |
| Wipe models only | `rm -rf /data/caller/speech-models/*` then re-run `speech-models` job |
| Disk usage | `du -sh /data/caller/*` |

**Do not** store models or Postgres on the root EBS alone if it is small; everything listed under `/data/caller` is on the 100GB volume.

---

## 10. Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `speech-stt` unhealthy | Models missing under `/data/caller/speech-models/stt/nemotron` — re-run models job |
| `speech-tts` slow start / unhealthy | First load + CUDA compile; wait 5–10 min; check `nvidia-smi` |
| Caddy no cert | `APP_DOMAIN` wrong, port 80 blocked, or DNS not pointing at this host |
| `bootstrap_dograh` fails | `DOGRAH_API_KEY` empty or Dograh not on `caller` network |
| SSH timeout from laptop | Security group / instance stopped — not an app issue |
| Out of disk on `/data` | Models + Postgres + HF cache; prune unused Docker images: `docker system prune -a` (careful) |

---

## 11. Cursor agent checklist

- [ ] EBS mounted at `/data`, fstab entry, dirs under `/data/caller`
- [ ] `nvidia-smi` + GPU in Docker works
- [ ] Repo cloned `selfhost`, `fetch_dograh.sh` done
- [ ] `.env` filled (domain, secrets, LLM key, Dograh key when available)
- [ ] `speech-models` job completed on EBS path
- [ ] `docker compose` **with** `docker-compose.data.yml` — full stack healthy
- [ ] Dograh up with `dograh.override.yml` on network `caller`
- [ ] `bootstrap_dograh` succeeded
- [ ] HTTPS site loads; speech `/health` OK
- [ ] Report back: public URL, `nvidia-smi` memory at idle, any log errors

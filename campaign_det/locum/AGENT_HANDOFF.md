# Agent Handoff: locum (Dr. Locum)

## Goal
Outbound Hindi female-voice calls to doctors near a posted temporary (locum) job. Tell them the job is on the **Dr. Locum** app, share the job facts from the partner API, and **record whether they are interested**.

## Fixed campaign id
`4e377637-2559-4707-9963-b13652dc7f96`

Create it with:

```bash
cd backend && python manage.py ensure_locum_campaign
```

## Files
- `campaign_form.json` — Campaign / CampaignContext / AgentProfile values
- `context_guard/dialogue/graphs/locum.json` — dialogue graph (must keep the same campaign id)
- `backend/apps/campaigns/locum_source.py` — **placeholder** partner API (phone + job)
- `LocumInterest` model — phone, job fields, interested yes/no/unknown

## Runtime behaviour
1. `POST /api/campaigns/<id>/sync-locum/` pulls placeholder leads and queues calls.
2. Per-call job facts are loaded into the context guard via `call_request_id`.
3. Scripted job lines fill `{job_title}`, `{job_location}`, `{job_specialty}`, `{job_duration}`, `{job_facility}`.
4. A yes/no on the `job` or `interest` step (or a clear yes after `persuade`) is saved on `LocumInterest`.
5. Dashboard: `/app/locum`.

## Replace the placeholder
Point `fetch_locum_leads()` in `locum_source.py` at the real partner API. Keep the same dict shape (`phone_e164`, `doctor_name`, `job_*` fields).

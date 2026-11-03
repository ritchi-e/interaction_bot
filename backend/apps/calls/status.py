"""Map a Dograh run webhook into one of our call records."""

import json
from datetime import timezone as dt_timezone

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.calls.models import CallAttempt, CallRequest

HANDOFF_DISPOSITIONS = {"handoff_requested", "handoff", "human_handoff"}

# Engine-observed termination, not an inferred disposition.
# https://docs.dograh.com/developer/webhooks — gathered_context.call_status
AGENT_END_REASONS = {"end_call", "agent_hangup", "assistant_hangup", "bot_hangup"}
CALLER_END_REASONS = {"user_hangup", "caller_hangup", "customer_hangup", "remote_hangup"}
# Dograh Status webhooks often send status=completed with end_reason=busy /
# no_answer when the carrier never connected media. Prefer the end reason.
FAILED_END_REASONS = {
    "busy",
    "user_busy",
    "no_answer",
    "noanswer",
    "no-answer",
    "failed",
    "error",
    "rejected",
    "cancel",
    "cancelled",
    "canceled",
}

STATUS_MAP = {
    "completed": "completed",
    "ended": "completed",
    "failed": "failed",
    "error": "failed",
    "no-answer": "failed",
    "no_answer": "failed",
    "busy": "failed",
    "in_progress": "in_progress",
    "in-progress": "in_progress",
    "ringing": "dialing",
    "dialing": "dialing",
}


def _as_dict(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _dig(payload, *path):
    current = payload
    for key in path:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return current or ""


def _seconds(value):
    if value is None or value == "":
        return None
    try:
        seconds = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return seconds


def _when(value):
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = parse_datetime(value.strip())
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


def ended_by_from_reason(reason):
    value = (reason or "").strip().lower().replace("-", "_").replace(" ", "_")
    if value in AGENT_END_REASONS:
        return "agent"
    if value in CALLER_END_REASONS:
        return "caller"
    return ""


def interpret(payload):
    initial = _as_dict(payload.get("initial_context"))
    gathered = _as_dict(payload.get("gathered_context"))
    metadata = _as_dict(payload.get("metadata"))
    cost = _as_dict(payload.get("cost_info"))
    call_request_id = (
        str(initial.get("call_request_id") or metadata.get("call_request_id") or payload.get("call_request_id") or "")
    )
    run_id = str(
        payload.get("run_id")
        or payload.get("workflow_run_id")
        or payload.get("id")
        or _dig(payload, "run", "id")
        or ""
    )
    raw_status = str(payload.get("status") or payload.get("event") or "").lower()
    if raw_status.startswith("run."):
        raw_status = raw_status.split(".", 1)[1]
    disposition = str(
        payload.get("disposition")
        or payload.get("call_disposition")
        or gathered.get("call_disposition")
        or gathered.get("disposition")
        or ""
    ).lower()
    transcript = str(payload.get("transcript") or payload.get("transcript_text") or "")
    recording_url = str(payload.get("recording_url") or "")
    raw_reason = (
        payload.get("end_reason")
        or payload.get("call_status")
        or gathered.get("call_status")
        or gathered.get("end_reason")
        or ""
    )
    end_reason = str(raw_reason).strip().lower().replace("-", "_").replace(" ", "_")[:80]
    mapped = STATUS_MAP.get(raw_status, "")
    disposition_key = disposition.strip().lower().replace("-", "_").replace(" ", "_")
    if end_reason in FAILED_END_REASONS or disposition_key in FAILED_END_REASONS:
        mapped = "failed"
    duration = payload.get("duration_seconds")
    if duration in (None, ""):
        duration = payload.get("duration")
    if duration in (None, ""):
        duration = cost.get("call_duration_seconds")
    return {
        "call_request_id": call_request_id,
        "run_id": run_id,
        "status": mapped,
        "disposition": disposition,
        "transcript": transcript,
        "recording_url": recording_url,
        "handoff": disposition in HANDOFF_DISPOSITIONS,
        "started_at": _when(payload.get("call_time") or payload.get("started_at") or ""),
        "duration_seconds": _seconds(duration),
        "end_reason": end_reason,
        "ended_by": ended_by_from_reason(end_reason),
    }


def find_call_request(parsed):
    if parsed["call_request_id"]:
        try:
            return CallRequest.objects.select_related(
                "lead", "campaign", "campaign__context", "organisation", "organisation__whatsapp"
            ).get(pk=parsed["call_request_id"])
        except (CallRequest.DoesNotExist, ValueError):
            pass
    if parsed["run_id"]:
        attempt = (
            CallAttempt.objects.select_related(
                "call_request",
                "call_request__lead",
                "call_request__campaign",
                "call_request__campaign__context",
                "call_request__organisation",
                "call_request__organisation__whatsapp",
            )
            .filter(dograh_run_id=parsed["run_id"])
            .first()
        )
        if attempt:
            return attempt.call_request
    return None

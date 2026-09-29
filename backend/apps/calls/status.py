"""Map a Dograh run webhook into one of our call records."""

from apps.calls.models import CallAttempt, CallRequest

HANDOFF_DISPOSITIONS = {"handoff_requested", "handoff", "human_handoff"}

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


def _dig(payload, *path):
    current = payload
    for key in path:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return current or ""


def interpret(payload):
    initial = payload.get("initial_context") if isinstance(payload.get("initial_context"), dict) else {}
    gathered = payload.get("gathered_context") if isinstance(payload.get("gathered_context"), dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    call_request_id = (
        str(initial.get("call_request_id") or metadata.get("call_request_id") or payload.get("call_request_id") or "")
    )
    run_id = str(payload.get("run_id") or payload.get("id") or _dig(payload, "run", "id") or "")
    raw_status = str(payload.get("status") or payload.get("event") or "").lower()
    if raw_status.startswith("run."):
        raw_status = raw_status.split(".", 1)[1]
    disposition = str(payload.get("disposition") or gathered.get("disposition") or "").lower()
    transcript = str(payload.get("transcript") or payload.get("transcript_text") or "")
    recording_url = str(payload.get("recording_url") or "")
    return {
        "call_request_id": call_request_id,
        "run_id": run_id,
        "status": STATUS_MAP.get(raw_status, ""),
        "disposition": disposition,
        "transcript": transcript,
        "recording_url": recording_url,
        "handoff": disposition in HANDOFF_DISPOSITIONS,
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

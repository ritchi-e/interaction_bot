"""Partner API that supplies doctors to call and the matching locum job.

Replace ``fetch_locum_leads`` with a real HTTP client when the partner endpoint
is ready. Keep the returned dict shape stable so sync and the dialogue stay
unchanged.
"""

from __future__ import annotations

import os
from typing import Any

# Optional override once the partner goes live, e.g.
# LOCUM_PARTNER_API_URL=https://partner.example/api/v1/nearby-doctors
LOCUM_PARTNER_API_URL = (os.environ.get("LOCUM_PARTNER_API_URL") or "").strip()


def fetch_locum_leads() -> list[dict[str, Any]]:
    """Return phone numbers and job payloads for outbound locum calls.

    Each item must include:
      phone_e164, doctor_name,
      job_id, job_title, job_location, job_specialty, job_duration, job_facility
    Optional: job_details (dict), source_payload (raw partner body).
    """
    if LOCUM_PARTNER_API_URL:
        return _fetch_from_partner(LOCUM_PARTNER_API_URL)
    return placeholder_leads()


def placeholder_leads() -> list[dict[str, Any]]:
    """Sample rows used until the partner API is wired in."""
    return [
        {
            "phone_e164": "+919876543210",
            "doctor_name": "Dr. Anita Sharma",
            "job_id": "job-demo-001",
            "job_title": "Emergency duty doctor",
            "job_location": "Andheri East, Mumbai",
            "job_specialty": "General Medicine",
            "job_duration": "सात दिन",
            "job_facility": "City Care Hospital",
            "job_details": {
                "shift": "night",
                "start_date": "2026-11-05",
                "notes": "Placeholder job from locum_source.placeholder_leads",
            },
            "source_payload": {"source": "placeholder", "id": "job-demo-001"},
        },
        {
            "phone_e164": "+919811122233",
            "doctor_name": "Dr. Rohan Mehta",
            "job_id": "job-demo-002",
            "job_title": "OPD cover",
            "job_location": "Baner, Pune",
            "job_specialty": "Pediatrics",
            "job_duration": "तीन दिन",
            "job_facility": "Sunrise Children's Clinic",
            "job_details": {
                "shift": "day",
                "start_date": "2026-11-08",
                "notes": "Placeholder job from locum_source.placeholder_leads",
            },
            "source_payload": {"source": "placeholder", "id": "job-demo-002"},
        },
    ]


def _fetch_from_partner(url: str) -> list[dict[str, Any]]:
    """HTTP placeholder. Map the partner JSON into our lead shape when live."""
    import httpx

    response = httpx.get(url, timeout=15.0)
    response.raise_for_status()
    payload = response.json()
    rows = payload if isinstance(payload, list) else payload.get("results") or payload.get("data") or []
    leads: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        job = item.get("job") if isinstance(item.get("job"), dict) else item
        phone = str(item.get("phone_e164") or item.get("phone") or "").strip()
        if not phone:
            continue
        leads.append(
            {
                "phone_e164": phone,
                "doctor_name": str(item.get("doctor_name") or item.get("name") or "").strip(),
                "job_id": str(job.get("job_id") or job.get("id") or "").strip(),
                "job_title": str(job.get("job_title") or job.get("title") or "").strip(),
                "job_location": str(job.get("job_location") or job.get("location") or "").strip(),
                "job_specialty": str(job.get("job_specialty") or job.get("specialty") or "").strip(),
                "job_duration": str(job.get("job_duration") or job.get("duration") or "").strip(),
                "job_facility": str(job.get("job_facility") or job.get("facility") or "").strip(),
                "job_details": job.get("job_details") if isinstance(job.get("job_details"), dict) else {},
                "source_payload": item,
            }
        )
    return leads


def job_facts_lines(row: dict[str, Any]) -> str:
    """Plain FACTS block lines for the context guard."""
    parts = [
        f"Doctor name (if known): {row.get('doctor_name') or 'unknown'}",
        f"Job id: {row.get('job_id') or 'unknown'}",
        f"Job title: {row.get('job_title') or 'temporary doctor duty'}",
        f"Location: {row.get('job_location') or 'nearby'}",
        f"Specialty: {row.get('job_specialty') or 'general'}",
        f"Duration: {row.get('job_duration') or 'short term'}",
        f"Facility: {row.get('job_facility') or 'the listed hospital or clinic'}",
        "App: Dr. Locum — the job is posted on this app; applications are completed in the app.",
        "Do not invent salary, contract terms, or guarantee selection.",
    ]
    return "\n".join(parts)


def template_vars(row: dict[str, Any]) -> dict[str, str]:
    """Values for dialogue graph placeholders like {job_title}."""
    return {
        "doctor_name": str(row.get("doctor_name") or "डॉक्टर").strip() or "डॉक्टर",
        "job_id": str(row.get("job_id") or "").strip(),
        "job_title": str(row.get("job_title") or "अस्थायी डॉक्टर ड्यूटी").strip() or "अस्थायी डॉक्टर ड्यूटी",
        "job_location": str(row.get("job_location") or "आपके नज़दीक").strip() or "आपके नज़दीक",
        "job_specialty": str(row.get("job_specialty") or "जनरल").strip() or "जनरल",
        "job_duration": str(row.get("job_duration") or "कुछ दिन").strip() or "कुछ दिन",
        "job_facility": str(row.get("job_facility") or "अस्पताल").strip() or "अस्पताल",
    }

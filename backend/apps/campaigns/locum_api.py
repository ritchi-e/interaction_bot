"""Locum interest rows: list for the dashboard, save from the guard, sync from partner API."""

from __future__ import annotations

import uuid

from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.calls.models import CallRequest, Lead
from apps.calls.services import apply_decision
from apps.campaigns.locum_source import fetch_locum_leads, job_facts_lines, placeholder_leads, template_vars
from apps.campaigns.models import Campaign, LocumInterest
from apps.campaigns.serializers import LocumInterestSerializer
from apps.campaigns.views import require_internal
from apps.compliance.models import CallPermission
from apps.compliance.phones import normalise_indian_mobile

LOCUM_CAMPAIGN_ID = "4e377637-2559-4707-9963-b13652dc7f96"


def locum_payload(row: LocumInterest) -> dict:
    data = {
        "id": str(row.id),
        "phone_e164": row.phone_e164,
        "doctor_name": row.doctor_name,
        "job_id": row.job_id,
        "job_title": row.job_title,
        "job_location": row.job_location,
        "job_specialty": row.job_specialty,
        "job_duration": row.job_duration,
        "job_facility": row.job_facility,
        "job_details": row.job_details or {},
        "interested": row.interested,
        "facts": job_facts_lines(
            {
                "doctor_name": row.doctor_name,
                "job_id": row.job_id,
                "job_title": row.job_title,
                "job_location": row.job_location,
                "job_specialty": row.job_specialty,
                "job_duration": row.job_duration,
                "job_facility": row.job_facility,
            }
        ),
        "templates": template_vars(
            {
                "doctor_name": row.doctor_name,
                "job_id": row.job_id,
                "job_title": row.job_title,
                "job_location": row.job_location,
                "job_specialty": row.job_specialty,
                "job_duration": row.job_duration,
                "job_facility": row.job_facility,
            }
        ),
    }
    return data


def apply_lead_fields(row: LocumInterest, lead: dict) -> None:
    row.doctor_name = str(lead.get("doctor_name") or row.doctor_name or "")[:200]
    row.job_id = str(lead.get("job_id") or row.job_id or "")[:120]
    row.job_title = str(lead.get("job_title") or row.job_title or "")[:300]
    row.job_location = str(lead.get("job_location") or row.job_location or "")[:300]
    row.job_specialty = str(lead.get("job_specialty") or row.job_specialty or "")[:200]
    row.job_duration = str(lead.get("job_duration") or row.job_duration or "")[:120]
    row.job_facility = str(lead.get("job_facility") or row.job_facility or "")[:300]
    if isinstance(lead.get("job_details"), dict):
        row.job_details = lead["job_details"]
    if isinstance(lead.get("source_payload"), dict):
        row.source_payload = lead["source_payload"]


def ensure_placeholder_for_call(campaign: Campaign, call_request: CallRequest) -> LocumInterest:
    """Test calls still need a job payload so the agent has something to say."""
    existing = LocumInterest.objects.filter(call_request=call_request).order_by("-created_at").first()
    if existing is not None:
        return existing
    sample = placeholder_leads()[0]
    phone = call_request.lead.phone_e164 if call_request.lead_id else sample["phone_e164"]
    row = LocumInterest(
        organisation=campaign.organisation,
        campaign=campaign,
        call_request=call_request,
        phone_e164=phone,
    )
    apply_lead_fields(row, sample)
    row.save()
    return row


class LocumInterestListView(generics.ListAPIView):
    serializer_class = LocumInterestSerializer

    def get_queryset(self):
        organisation = self.request.user.organisation
        if organisation is None:
            return LocumInterest.objects.none()
        return LocumInterest.objects.filter(organisation=organisation).select_related("campaign")


class InternalLocumJobView(APIView):
    """Job facts + template vars for the active call."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        require_internal(request)
        call_id = str(request.query_params.get("call_request_id") or "").strip()
        if not call_id:
            return Response({"detail": "call_request_id required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            uuid.UUID(call_id)
        except ValueError:
            return Response({"detail": "invalid call_request_id"}, status=status.HTTP_400_BAD_REQUEST)
        row = LocumInterest.objects.filter(call_request_id=call_id).order_by("-created_at").first()
        if row is None:
            call = CallRequest.objects.select_related("campaign", "lead").filter(pk=call_id).first()
            if call is None or str(call.campaign_id) != LOCUM_CAMPAIGN_ID:
                return Response({"detail": "no locum job for this call"}, status=status.HTTP_404_NOT_FOUND)
            row = ensure_placeholder_for_call(call.campaign, call)
        return Response(locum_payload(row))


class InternalLocumInterestView(APIView):
    """Record whether the doctor is interested in the job on this call."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        require_internal(request)
        interested = str(request.data.get("interested") or "").strip().lower()
        if interested in {"true", "1", "yes", "interested"}:
            value = "yes"
        elif interested in {"false", "0", "no", "not_interested", "not interested"}:
            value = "no"
        else:
            return Response({"detail": "interested must be yes or no"}, status=status.HTTP_400_BAD_REQUEST)
        campaign = Campaign.objects.filter(pk=request.data.get("campaign_id"), is_active=True).first()
        if campaign is None:
            return Response({"detail": "unknown campaign"}, status=status.HTTP_404_NOT_FOUND)
        call = None
        call_id = str(request.data.get("call_request_id") or "").strip()
        if call_id:
            try:
                uuid.UUID(call_id)
            except ValueError:
                call_id = ""
        if call_id:
            call = CallRequest.objects.select_related("lead").filter(pk=call_id, campaign=campaign).first()
        row = None
        if call is not None:
            row = LocumInterest.objects.filter(call_request=call).order_by("-created_at").first()
        if row is None:
            phone = ""
            if call is not None and call.lead_id:
                phone = call.lead.phone_e164
            phone = str(request.data.get("phone_e164") or phone or "").strip()
            if not phone:
                return Response({"detail": "no locum row and no phone"}, status=status.HTTP_400_BAD_REQUEST)
            row = LocumInterest.objects.create(
                organisation=campaign.organisation,
                campaign=campaign,
                call_request=call,
                phone_e164=phone,
                doctor_name=str(request.data.get("doctor_name") or "")[:200],
                job_id=str(request.data.get("job_id") or "")[:120],
                job_title=str(request.data.get("job_title") or "")[:300],
            )
        row.interested = value
        row.save(update_fields=["interested", "updated_at"])
        if call is not None:
            call.disposition = "interested" if value == "yes" else "not_interested"
            call.save(update_fields=["disposition", "updated_at"])
        return Response(locum_payload(row))


class SyncLocumLeadsView(APIView):
    """Pull partner (or placeholder) leads and queue outbound calls for this campaign."""

    def post(self, request, pk=None):
        campaign = Campaign.objects.filter(pk=pk, organisation=request.user.organisation, is_active=True).first()
        if campaign is None:
            return Response({"detail": "unknown campaign"}, status=status.HTTP_404_NOT_FOUND)
        if str(campaign.id) != LOCUM_CAMPAIGN_ID:
            return Response(
                {"detail": "sync-locum is only for the locum campaign"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            leads = fetch_locum_leads()
        except Exception as exc:  # noqa: BLE001 — surface partner/placeholder errors to the UI
            return Response({"detail": f"partner API failed: {exc}"}, status=status.HTTP_502_BAD_GATEWAY)
        created = []
        with transaction.atomic():
            for lead in leads:
                phone = normalise_indian_mobile(lead.get("phone_e164") or lead.get("phone") or "")
                if phone is None:
                    continue
                person, _ = Lead.objects.get_or_create(
                    organisation=campaign.organisation,
                    phone_e164=phone,
                    defaults={"name": str(lead.get("doctor_name") or "")[:200], "campaign": campaign},
                )
                if lead.get("doctor_name") and not person.name:
                    person.name = str(lead.get("doctor_name"))[:200]
                    person.campaign = campaign
                    person.save(update_fields=["name", "campaign", "updated_at"])
                if not CallPermission.objects.filter(
                    organisation=campaign.organisation, phone_e164=phone
                ).exists():
                    CallPermission.objects.create(
                        organisation=campaign.organisation,
                        phone_e164=phone,
                        is_permanent=True,
                    )
                call_request = CallRequest.objects.create(
                    organisation=campaign.organisation,
                    lead=person,
                    campaign=campaign,
                    status="queued",
                )
                row = LocumInterest(
                    organisation=campaign.organisation,
                    campaign=campaign,
                    call_request=call_request,
                    phone_e164=phone,
                )
                apply_lead_fields(row, lead)
                row.save()
                apply_decision(call_request)
                call_request.refresh_from_db()
                created.append(
                    {
                        "locum_interest_id": str(row.id),
                        "call_request_id": str(call_request.id),
                        "phone_e164": phone,
                        "job_id": row.job_id,
                        "status": call_request.status,
                    }
                )
        return Response({"queued": len(created), "items": created}, status=status.HTTP_201_CREATED)

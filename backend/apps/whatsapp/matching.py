import uuid

from apps.campaigns.models import Campaign, CampaignKeyword, OutboundTemplateMessage

CAMPAIGN_PREFIX = "campaign:"


def _uuid_or_none(value):
    text = (value or "").strip()
    if text.startswith(CAMPAIGN_PREFIX):
        text = text[len(CAMPAIGN_PREFIX) :]
    try:
        return uuid.UUID(text)
    except (ValueError, AttributeError):
        return None


def match_campaign(organisation, *, context_id="", button_payload="", body=""):
    if context_id:
        outbound = (
            OutboundTemplateMessage.objects.select_related("campaign")
            .filter(wa_message_id=context_id, campaign__organisation=organisation, campaign__is_active=True)
            .first()
        )
        if outbound:
            return outbound.campaign, "reply_context"

    campaign_id = _uuid_or_none(button_payload)
    if campaign_id:
        campaign = Campaign.objects.filter(pk=campaign_id, organisation=organisation, is_active=True).first()
        if campaign:
            return campaign, "button_payload"

    folded = (body or "").casefold()
    best = None
    if folded:
        keywords = CampaignKeyword.objects.select_related("campaign").filter(
            campaign__organisation=organisation, campaign__is_active=True
        )
        for rule in keywords:
            if rule.keyword.casefold() in folded:
                if best is None or len(rule.keyword) > len(best.keyword):
                    best = rule
        if best:
            return best.campaign, "keyword"

    default = Campaign.objects.filter(organisation=organisation, is_default=True, is_active=True).first()
    if default:
        return default, "default"
    return None, "unmatched"

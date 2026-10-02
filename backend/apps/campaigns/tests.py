import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.campaigns.models import Campaign
from apps.campaigns.prompt_compiler import compile_system_prompt
from apps.tenants.services import create_organisation


@pytest.mark.django_db
def test_prompt_contains_only_given_facts():
    user = create_organisation("Sundaram Loans", "ops@sundaram.test", "supersecret1")
    campaign = Campaign.objects.create(
        organisation=user.organisation, name="Personal loan replies", language="hi", is_default=True
    )
    campaign.context.agent_name = "Meera"
    campaign.context.goal = "Explain the loan offer the customer asked about."
    campaign.context.offer_details = "Personal loan up to the amount shown below, tenure 12 months."
    campaign.context.prices = [{"label": "Processing fee", "amount": "499"}]
    campaign.context.faqs = [{"question": "Is there a joining fee?", "answer": "No joining fee."}]
    campaign.context.forbidden_topics = ["interest waiver"]
    campaign.context.competitors = ["EasyCredit"]
    campaign.context.handoff_message = "यह जानकारी मेरे पास नहीं है। हमारी टीम आपको कॉल करेगी।"
    campaign.context.save()

    prompt = compile_system_prompt(campaign)

    assert "Rs 499" in prompt
    assert "No joining fee." in prompt
    assert "Never invent a price" in prompt
    assert "यह जानकारी मेरे पास नहीं है।" in prompt
    assert "Speak Hindi in Devanagari" in prompt
    assert "जी, बिल्कुल।" in prompt
    assert "90%" not in prompt
    assert "EasyCredit" not in prompt


@pytest.mark.django_db
def test_create_response_includes_saved_facts():
    user = create_organisation("Sundaram Loans", "ops@sundaram.test", "supersecret1")
    client = APIClient()
    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    response = client.post(
        "/api/campaigns/",
        {
            "name": "Loan replies",
            "language": "hi",
            "agent_name": "Meera",
            "offer_details": "Personal loan, 12 month tenure.",
            "prices": [{"label": "Processing fee", "amount": "499"}],
            "keywords": ["loan"],
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["agent_name"] == "Meera"
    assert response.data["offer_details"] == "Personal loan, 12 month tenure."
    assert response.data["prices"] == [{"label": "Processing fee", "amount": "499"}]
    assert response.data["keywords"] == ["loan"]

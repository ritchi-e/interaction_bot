"""Create or refresh the locum campaign with the fixed UUID the dialogue graph uses."""

from django.core.management.base import BaseCommand

from apps.agents.models import AgentProfile
from apps.campaigns.locum_api import LOCUM_CAMPAIGN_ID
from apps.campaigns.models import Campaign, CampaignContext, CampaignKeyword
from apps.tenants.models import Organisation

FORM = {
    "name": "locum",
    "language": "hi",
    "tts_voice": "female",
    "agent_name": "प्रिया",
    "goal": (
        "डॉक्टर को बताना कि Dr. Locum ऐप पर उनके नज़दीक एक अस्थायी (locum) जॉब पोस्ट हुई है, "
        "जॉब की जानकारी साझा करना, और साफ़ पूछना कि वे इस जॉब में दिलचस्पी रखते हैं या नहीं।"
    ),
    "offer_details": (
        "Dr. Locum एक ऐप है जहाँ अस्पताल और क्लिनिक अस्थायी डॉक्टर जॉब पोस्ट करते हैं। "
        "हर कॉल पर जॉब का शीर्षक, स्थान, विशेषज्ञता, अवधि और सुविधा का नाम पार्टनर API से आता है। "
        "इस अभियान में वेतन, अनुबंध की शर्तें, या आवेदन जमा करने का वादा अपुष्ट होने पर नहीं बताया जाता। "
        "दिलचस्पी हाँ या नहीं के रूप में रिकॉर्ड होती है; आवेदन ऐप पर ही पूरा होता है।"
    ),
    "faqs": [
        {
            "question": "Dr. Locum क्या है?",
            "answer": "Dr. Locum एक ऐप है जहाँ डॉक्टरों के लिए अस्थायी जॉब पोस्ट होती हैं। आप ऐप पर जॉब देख और आवेदन कर सकते हैं।",
        },
        {
            "question": "वेतन कितना मिलेगा?",
            "answer": "इस कॉल में वेतन की पुष्टि उपलब्ध नहीं है। सही राशि आपको Dr. Locum ऐप पर जॉब खोलकर दिखेगी।",
        },
        {
            "question": "आवेदन कैसे करें?",
            "answer": "Dr. Locum ऐप खोलकर इस जॉब को देखें और वहीं से आवेदन पूरा करें।",
        },
    ],
    "allowed_topics": [
        "Dr. Locum ऐप",
        "अस्थायी डॉक्टर जॉब",
        "locum जॉब",
        "जॉब का स्थान और विशेषज्ञता",
        "जॉब की अवधि",
        "ऐप पर जॉब देखने और आवेदन करने का तरीका",
        "इस जॉब में दिलचस्पी",
    ],
    "forbidden_topics": [
        "गारंटीड जॉब",
        "गारंटीड सैलरी",
        "अपुष्ट वेतन",
        "अपुष्ट अनुबंध",
        "इस कॉल पर आवेदन जमा करना",
    ],
    "handoff_message": "इसकी सही जानकारी अभी पुष्टि उपलब्ध नहीं है। पूरी डिटेल आपको Dr. Locum ऐप पर मिल जाएगी।",
    "greeting": "नमस्ते, मैं प्रिया बोल रही हूँ, Dr. Locum से। क्या आपसे एक मिनट बात कर सकती हूँ?",
    "closing_line": "आपके समय के लिए धन्यवाद। Dr. Locum ऐप ज़रूर देखिएगा। आपका दिन अच्छा रहे।",
    "role": "Dr. Locum की जॉब सलाहकार",
    "persona": (
        "गर्मजोशी वाली, सहज और विनम्र। डॉक्टरों से छोटे वाक्यों में सरल हिंदी में बात करती है। "
        "हमेशा 'आप' कहती है। दबाव नहीं डालती, और दिलचस्पी का जवाब साफ़ पूछती है।"
    ),
    "keywords": ["locum", "Dr. Locum", "डॉक्टर जॉब", "अस्थायी जॉब"],
    "permission_message": "नमस्ते! Dr. Locum पर एक अस्थायी जॉब के बारे में बात करने के लिए कृपया 'हाँ' लिखकर भेजिए।",
}


class Command(BaseCommand):
    help = "Ensure the locum campaign exists with the dialogue-graph UUID and Hindi female voice."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organisation",
            default="",
            help="Organisation slug or name. Defaults to the first organisation.",
        )

    def handle(self, *args, **options):
        org = self._organisation(options.get("organisation") or "")
        if org is None:
            self.stderr.write("No organisation found. Create one before seeding locum.")
            return
        campaign, created = Campaign.objects.get_or_create(
            id=LOCUM_CAMPAIGN_ID,
            defaults={
                "organisation": org,
                "name": FORM["name"],
                "language": FORM["language"],
                "tts_voice": FORM["tts_voice"],
                "permission_message": FORM["permission_message"],
                "is_active": True,
            },
        )
        if not created:
            campaign.organisation = org
            campaign.name = FORM["name"]
            campaign.language = FORM["language"]
            campaign.tts_voice = FORM["tts_voice"]
            campaign.permission_message = FORM["permission_message"]
            campaign.is_active = True
            campaign.save()
        context, _ = CampaignContext.objects.get_or_create(campaign=campaign)
        context.agent_name = FORM["agent_name"]
        context.goal = FORM["goal"]
        context.offer_details = FORM["offer_details"]
        context.faqs = FORM["faqs"]
        context.allowed_topics = FORM["allowed_topics"]
        context.forbidden_topics = FORM["forbidden_topics"]
        context.competitors = []
        context.prices = []
        context.handoff_message = FORM["handoff_message"]
        context.save()
        campaign.keywords.all().delete()
        CampaignKeyword.objects.bulk_create(
            [CampaignKeyword(campaign=campaign, keyword=word) for word in FORM["keywords"]]
        )
        profile, _ = AgentProfile.objects.get_or_create(campaign=campaign)
        profile.role = FORM["role"]
        profile.persona = FORM["persona"]
        profile.greeting = FORM["greeting"]
        profile.closing_line = FORM["closing_line"]
        profile.allow_interrupt = True
        profile.max_call_seconds = 300
        profile.save()
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} locum campaign {campaign.id} for {org.name}"))

    def _organisation(self, hint):
        qs = Organisation.objects.all().order_by("id")
        if hint:
            found = qs.filter(slug=hint).first() or qs.filter(name__iexact=hint).first()
            return found
        return qs.first()

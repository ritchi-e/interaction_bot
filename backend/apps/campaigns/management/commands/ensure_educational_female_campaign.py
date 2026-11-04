"""Create or refresh the educational female campaign."""

from django.core.management.base import BaseCommand

from apps.agents.models import AgentProfile
from apps.campaigns.models import Campaign, CampaignContext, CampaignKeyword
from apps.tenants.models import Organisation

CAMPAIGN_ID = "3b3de0de-e097-44e0-858c-a450b31ef8e9"

FORM = {'name': 'educational female', 'language': 'hinglish', 'tts_voice': 'female', 'permission_message': 'क्या आप इस कॉल पर ऑनलाइन पढ़ाई सहायक के बारे में जानकारी सुनने की अनुमति देते हैं?', 'agent_name': 'प्रिया', 'goal': 'Caller को online पढ़ाई assistant की available features से familiar कराना और यह समझना कि वह और जानकारी चाहता है या नहीं।', 'offer_details': 'यह online पढ़ाई assistant students को पढ़ाई के सवाल समझने, available study material से जानकारी खोजने और exam की तैयारी में मदद करता है। यह AI की मदद से पढ़ाई को आसान बनाने के लिए बनाया गया है। यह Smarty नाम का एक app है और Play Store पर download के लिए available है। इस campaign में price, subscription या result की पुष्टि नहीं की गई है।', 'prices': [], 'faqs': [{'answer': 'यह पढ़ाई के सवालों के जवाब देने और available study material समझने में मदद करता है।', 'question': 'यह क्या करता है?'}, {'answer': 'हाँ, यह exam की तैयारी और पढ़ाई के सवालों को समझने में मदद कर सकती है।', 'question': 'क्या यह exam की तैयारी में मदद करता है?'}, {'answer': 'नहीं, इसका purpose पढ़ाई में मदद करना है, teacher की जगह लेना नहीं।', 'question': 'क्या यह teacher की जगह लेता है?'}, {'answer': 'इस campaign में price की पुष्टि available नहीं है। मैं अपुष्ट price नहीं बताना चाहूँगी।', 'question': 'इसकी price कितनी है?'}, {'answer': 'AI से मिले जवाबों को जाँचना अच्छा रहता है। यह पढ़ाई में मदद करने वाला assistant है, हर जवाब की guarantee नहीं।', 'question': 'क्या यह मेरे सभी सवालों का सही जवाब देगा?'}, {'answer': 'इस campaign में WhatsApp पर जानकारी भेजने की facility की पुष्टि नहीं है, इसलिए मैं इसका वादा नहीं कर सकती।', 'question': 'क्या आप मुझे जानकारी WhatsApp पर भेज सकते हैं?'}, {'answer': 'यह Smarty नाम का app है। आप इसे Play Store से download कर सकते हैं।', 'question': 'यह app कहाँ मिलेगा और इसका नाम क्या है?'}], 'allowed_topics': ['online पढ़ाई', 'AI based पढ़ाई assistant', 'study material से जानकारी खोजना', 'पढ़ाई के सवाल', 'exam की तैयारी', 'AI जवाबों की limits', 'Smarty app', 'Play Store download'], 'forbidden_topics': ['गारंटीड परीक्षा परिणाम', 'गारंटीड अंक', 'नौकरी की गारंटी', 'अपुष्ट कीमत', 'अपुष्ट सदस्यता या भुगतान शर्तें', 'अपुष्ट उपलब्धता', 'अपुष्ट WhatsApp या callback वादा'], 'competitors': [], 'handoff_message': 'इस जानकारी की अभी पुष्टि available नहीं है। मैं इस बारे में कोई अपुष्ट बात नहीं बताना चाहूँगी।', 'role': 'ऑनलाइन शिक्षा सलाहकार', 'persona': 'विनम्र, सहज, मददगार और संक्षिप्त। रोजमर्रा की Hinglish बोलें: Hindi शब्द Devanagari में, English शब्द Latin में। एक समय में एक सवाल पूछें, और caller पर दबाव न डालें।', 'greeting': 'नमस्ते, मैं प्रिया बोल रही हूँ। क्या आपसे एक मिनट बात कर सकती हूँ?', 'closing_line': 'आपके समय के लिए धन्यवाद। आपका दिन अच्छा रहे।', 'allow_interrupt': True, 'max_call_seconds': 300, 'keywords': ['प्रिया', 'Priya']}


class Command(BaseCommand):
    help = "Ensure the educational female campaign exists with hinglish female voice and current script."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organisation",
            default="",
            help="Organisation slug or name. Defaults to the first organisation.",
        )
        parser.add_argument(
            "--publish",
            action="store_true",
            help="Also publish the agent to Dograh after seeding.",
        )

    def handle(self, *args, **options):
        org = self._organisation(options.get("organisation") or "")
        if org is None:
            self.stderr.write("No organisation found. Create one before seeding.")
            return
        campaign, created = Campaign.objects.get_or_create(
            id=CAMPAIGN_ID,
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
        context.competitors = FORM["competitors"]
        context.prices = FORM["prices"]
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
        profile.allow_interrupt = FORM["allow_interrupt"]
        profile.max_call_seconds = FORM["max_call_seconds"]
        profile.save()
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} {FORM['name']} campaign {campaign.id} for {org.name}"))
        if options.get("publish"):
            from apps.agents.publish import publish_agent
            publish_agent(profile)
            self.stdout.write(self.style.SUCCESS(f"Published workflow {profile.dograh_workflow_uuid}"))

    def _organisation(self, hint):
        qs = Organisation.objects.all().order_by("id")
        if hint:
            found = qs.filter(slug=hint).first() or qs.filter(name__iexact=hint).first()
            return found
        return qs.first()

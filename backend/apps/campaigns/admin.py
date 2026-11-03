from django.contrib import admin

from apps.campaigns.models import (
    Appointment,
    Campaign,
    CampaignContext,
    CampaignKeyword,
    LocumInterest,
    OutboundTemplateMessage,
)

admin.site.register(Campaign)
admin.site.register(CampaignContext)
admin.site.register(CampaignKeyword)
admin.site.register(OutboundTemplateMessage)
admin.site.register(Appointment)
admin.site.register(LocumInterest)

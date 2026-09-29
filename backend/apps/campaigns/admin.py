from django.contrib import admin

from apps.campaigns.models import Campaign, CampaignContext, CampaignKeyword, OutboundTemplateMessage

admin.site.register(Campaign)
admin.site.register(CampaignContext)
admin.site.register(CampaignKeyword)
admin.site.register(OutboundTemplateMessage)

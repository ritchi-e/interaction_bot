from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.campaigns.models import Campaign, CampaignContext


@receiver(post_save, sender=Campaign)
def ensure_context(sender, instance, created, **kwargs):
    if created:
        CampaignContext.objects.get_or_create(campaign=instance)

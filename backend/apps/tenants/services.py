import secrets

from django.utils.text import slugify

from apps.tenants.models import (
    BusinessProfile,
    Organisation,
    ProviderKeys,
    User,
    WhatsAppCalling,
    WhatsAppConnection,
)


def unique_slug(name):
    base = slugify(name)[:60] or "org"
    slug = base
    index = 2
    while Organisation.objects.filter(slug=slug).exists():
        slug = f"{base}-{index}"
        index += 1
    return slug


def create_organisation(name, email, password):
    organisation = Organisation.objects.create(name=name, slug=unique_slug(name))
    user = User.objects.create_user(email=email, password=password, organisation=organisation)
    BusinessProfile.objects.create(organisation=organisation, display_name=name)
    WhatsAppConnection.objects.create(organisation=organisation, verify_token=secrets.token_urlsafe(24))
    WhatsAppCalling.objects.create(
        organisation=organisation,
        asterisk_endpoint="wa_" + organisation.slug.replace("-", "_"),
        webhook_token=secrets.token_urlsafe(24),
    )
    ProviderKeys.objects.create(organisation=organisation)
    return user

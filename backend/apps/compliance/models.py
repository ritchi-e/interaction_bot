from django.db import models

from apps.common.models import TimeStampedModel
from apps.tenants.models import Organisation


class CallPermission(TimeStampedModel):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="call_permissions")
    phone_e164 = models.CharField(max_length=20)
    is_permanent = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class OptOut(TimeStampedModel):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="opt_outs")
    phone_e164 = models.CharField(max_length=20)
    reason = models.CharField(max_length=80, default="whatsapp_stop")

    class Meta:
        unique_together = [("organisation", "phone_e164")]

    def __str__(self):
        return f"{self.phone_e164} ({self.organisation_id})"

from django.contrib import admin

from apps.calls.models import CallAttempt, CallRequest, ContextViolation, HandoffAlert, Lead

admin.site.register(Lead)
admin.site.register(CallRequest)
admin.site.register(CallAttempt)
admin.site.register(ContextViolation)
admin.site.register(HandoffAlert)

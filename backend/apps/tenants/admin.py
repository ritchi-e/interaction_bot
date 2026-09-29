from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from apps.tenants.models import BusinessProfile, Organisation, ProviderKeys, User, WhatsAppCalling, WhatsAppConnection


class TenantUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "organisation")


class TenantUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ("email", "organisation", "is_active", "is_staff", "is_superuser")


@admin.register(User)
class TenantUserAdmin(UserAdmin):
    form = TenantUserChangeForm
    add_form = TenantUserCreationForm
    ordering = ("email",)
    list_display = ("email", "organisation", "is_staff")
    fieldsets = (
        (None, {"fields": ("email", "password", "organisation")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "organisation", "password1", "password2")}),)
    search_fields = ("email",)


admin.site.register(Organisation)
admin.site.register(BusinessProfile)
admin.site.register(WhatsAppConnection)
admin.site.register(WhatsAppCalling)
admin.site.register(ProviderKeys)

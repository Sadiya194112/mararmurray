from django.contrib import admin

from apps.common.models import (
    PrivacyPolicy,
    TermsConditions,
)


# Register the PrivacyPolicy model
@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ("id", "content")
    search_fields = ("content",)


# Register the TermsConditions model
@admin.register(TermsConditions)
class TermsConditionsAdmin(admin.ModelAdmin):
    list_display = ("id", "content")
    search_fields = ("content",)

from django.contrib import admin

from apps.common.models import (
    GardenPhoto,
    GardenPreference,
    GardenProject,
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


# Register the GardenProject model
@admin.register(GardenProject)
class GardenProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "created_at", "updated_at")
    search_fields = ("name", "user__username")


# Register the GardenPhoto model
@admin.register(GardenPhoto)
class GardenPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "quality_status", "quality_score", "created_at")
    search_fields = ("project__name",)


# Register the GardenPreference model
@admin.register(GardenPreference)
class GardenPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "project",
        "sunlight",
        "soil_type",
        "garden_type",
        "total_area_sq_ft",
        "created_at",
        "updated_at",
    )
    search_fields = ("project__name",)

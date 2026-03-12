from django.contrib import admin
from apps.gardens.models import GardenPhoto, GardenProject

@admin.register(GardenPhoto)
class GardenPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "quality_status", "quality_score", "created_at")
    list_filter = ("quality_status",)
    search_fields = ("user__username",)

@admin.register(GardenProject)
class GardenProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "sunlight", "soil_type", "garden_type", "created_at")
    list_filter = ("sunlight", "soil_type", "garden_type")
    search_fields = ("name", "user__username", "location")
    readonly_fields = ("created_at", "updated_at")

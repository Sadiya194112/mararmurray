from django.contrib import admin

from apps.plants.models import HarvestMetadata, Plant


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "common_name",
        "scientific_name",
        "plant_type",
        "color",
        "sunlight",
        "soil_type",
        "garden_type",
        "water",
    )
    search_fields = (
        "common_name",
        "scientific_name",
        "plant_type",
        "color",
        "sunlight",
        "soil_type",
        "water",
        "garden_type",
    )
    list_filter = (
        "plant_type",
        "soil_type",
        "garden_type",
        "sunlight",
        "difficulty",
        "color",
    )


@admin.register(HarvestMetadata)
class HarvestMetadataAdmin(admin.ModelAdmin):
    list_display = ("id", "last_processed_page", "updated_at")
    readonly_fields = ("last_processed_page", "updated_at")

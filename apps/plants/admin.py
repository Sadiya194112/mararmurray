from django.contrib import admin

from apps.plants.models import Plant


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "common_name",
        "scientific_name",
        "plant_type",
        "sunlight",
        "soil_type",
        "garden_type",
        # "color",
        "water",
    )
    search_fields = ("common_name", "scientific_name", "plant_type", "sunlight", "soil_type", "water", "garden_type")
    list_filter = ("plant_type", "sunlight", "difficulty")

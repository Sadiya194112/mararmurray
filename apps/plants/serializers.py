from rest_framework import serializers

from apps.plants.models import Plant


class PlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plant
        fields = [
            "common_name",
            "scientific_name",
            "plant_type",
            "description",
            "image",
            "main_image_url",
            "sunlight",
            "water",
            "spacing",
            "growth_size",
            "season",
            "difficulty",
            "care_guide",
            "bloom_spring",
            "bloom_summer",
            "bloom_fall",
            "bloom_winter",
            "shopping_link",
            "tags",
            "family",
            "propagation",
        ]
        extra_kwargs = {
            "plant_type": {"required": True, "allow_blank": False},
            "description": {"required": True, "allow_blank": False},
            "image": {"required": False, "allow_null": True},
            "water": {"required": True, "allow_blank": False},
            "spacing": {"required": True, "allow_blank": False},
            "growth_size": {"required": True, "allow_blank": False},
            "season": {"required": True, "allow_blank": False},
            "difficulty": {"required": True, "allow_blank": False},
            "care_guide": {"required": True, "allow_blank": False},
            "bloom_spring": {"required": True},
            "bloom_summer": {"required": True},
            "bloom_fall": {"required": True},
            "bloom_winter": {"required": True},
        }

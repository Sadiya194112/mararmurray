from rest_framework import serializers

from apps.gardens.models import GardenPhoto, GardenPlant, GardenProject
from apps.plants.serializers import PlantSerializer


class GardenProjectSerializer(serializers.ModelSerializer):
    """Serializer for creating and retrieving garden projects."""

    class Meta:
        model = GardenProject
        fields = [
            "id",
            "name",
            "photo",
            "location",
            "sunlight",
            "soil_type",
            "garden_type",
            "height_ft",
            "width_ft",
            "total_area_sq_ft",
            "blended_image",
            "composite_image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "blended_image",
            "composite_image",
        ]


class GardenPlantDetailSerializer(serializers.ModelSerializer):
    """Serializer for a placed plant inside a garden project."""

    plant = PlantSerializer(read_only=True)
    plant_id = serializers.IntegerField(source="plant.id", read_only=True)

    class Meta:
        model = GardenPlant
        fields = ["id", "plant_id", "plant", "x", "y", "scale"]


class GardenProjectDetailSerializer(GardenProjectSerializer):
    """Serializer for a single garden project with all placed plants."""

    plants = GardenPlantDetailSerializer(many=True, read_only=True)

    class Meta(GardenProjectSerializer.Meta):
        fields = GardenProjectSerializer.Meta.fields + ["plants"]


class GardenPhotoSerializer(serializers.ModelSerializer):
    """Serializer for uploading and analyzing garden photos."""

    class Meta:
        model = GardenPhoto
        fields = [
            "id",
            "image",
            "quality_status",
            "quality_score",
            "quality_issues",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "quality_status",
            "quality_score",
            "quality_issues",
            "created_at",
        ]


class GardenListSerializer(serializers.ModelSerializer):
    """Lightweight serializer used in list views."""

    blended_image_url = serializers.SerializerMethodField()

    class Meta:
        model = GardenProject
        fields = [
            "id",
            "name",
            "photo",
            "blended_image_url",
            "created_at",
        ]

    def get_blended_image_url(self, obj):
        request = self.context.get("request")
        if obj.blended_image and request:
            return request.build_absolute_uri(obj.blended_image.url)
        return None

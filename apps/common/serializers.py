from rest_framework import serializers

from apps.common.models import (
    GardenPhoto,
    GardenPreference,
    GardenProject,
    PrivacyPolicy,
    TermsConditions,
)


class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicy
        fields = ["id", "content"]


class TermsConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsConditions
        fields = ["id", "content"]


class GardenProjectSerializer(serializers.ModelSerializer):
    """Serializer for creating and retrieving garden projects."""

    class Meta:
        model = GardenProject
        fields = ["id", "user", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class GardenPhotoSerializer(serializers.ModelSerializer):
    """Serializer for uploading and analyzing garden photos."""

    class Meta:
        model = GardenPhoto
        fields = [
            "id",
            "project",
            "image",
            "quality_status",
            "quality_score",
            "quality_issues",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "quality_status",
            "quality_score",
            "quality_issues",
            "created_at",
        ]


class GardenPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for garden design preferences."""

    class Meta:
        model = GardenPreference
        fields = [
            "id",
            "project",
            "location",
            "latitude",
            "longitude",
            "sunlight",
            "soil_type",
            "garden_type",
            "total_area_sq_ft",
            "height_ft",
            "width_ft",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "project", "created_at", "updated_at"]

from rest_framework import serializers

from apps.gardens.models import GardenPlant
from apps.posts.models import Post, SavedPost


class PostSerializer(serializers.ModelSerializer):
    """Serializer for posts with images."""

    class Meta:
        model = Post
        fields = [
            "id",
            "user",
            "garden_project",
            "description",
            "image",
            "tags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class PostDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for posts with user info."""

    # user = UserSerializer(read_only=True)
    plant_count = serializers.SerializerMethodField()
    plants = serializers.SerializerMethodField()

    def get_plant_count(self, obj):
        if not obj.garden_project_id:
            return 0
        return GardenPlant.objects.filter(project_id=obj.garden_project_id).count()

    def get_plants(self, obj):
        if not obj.garden_project_id:
            return []

        placements = (
            GardenPlant.objects.filter(project_id=obj.garden_project_id)
            .select_related("plant")
            .order_by("id")
        )
        return [
            {
                "id": placement.plant.id,
                "name": placement.plant.common_name,
                "sunlight": placement.plant.sunlight,
                "water": placement.plant.water,
                "spacing": placement.plant.spacing,
                "growth_size": placement.plant.growth_size,
            }
            for placement in placements
        ]

    class Meta:
        model = Post
        fields = [
            "id",
            # "user",
            "garden_project",
            "description",
            "image",
            "tags",
            "plant_count",
            "plants",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SavedPostSerializer(serializers.ModelSerializer):
    """Serializer for a saved post — includes full post data."""

    post = PostDetailSerializer(read_only=True)
    saved_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = SavedPost
        fields = ["post", "saved_at"]

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.posts.models import Post, SavedPost


class PostSerializer(serializers.ModelSerializer):
    """Serializer for posts with images."""

    class Meta:
        model = Post
        fields = [
            "id",
            "user",
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

    class Meta:
        model = Post
        fields = [
            "id",
            # "user",
            "description",
            "image",
            "tags",
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


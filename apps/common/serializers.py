from rest_framework import serializers

from apps.common.models import (
    ContactMessage,
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


class DashboardPostSerializer(serializers.Serializer):
    """Flat serializer for admin dashboard latest posts list."""

    id = serializers.IntegerField()
    image = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_image = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    description = serializers.CharField()
    tags = serializers.CharField()
    status = serializers.CharField()

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else None

    def get_user_image(self, obj):
        request = self.context.get("request")
        if obj.user and obj.user.image and request:
            return request.build_absolute_uri(obj.user.image.url)
        return None


class ContactMessageSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField()

    def create(self, validated_data):
        return ContactMessage.objects.create(**validated_data)

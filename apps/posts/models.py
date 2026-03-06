from django.db import models

from apps.accounts.models import User


class Post(models.Model):
    """Model for user posts with images."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    description = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to="post_images/", null=True, blank=True)
    tags = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Comma-separated hashtags (e.g. #Rose,#Garden,#Spring)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["tags"]),
        ]

    def __str__(self):
        return f"Post by {self.user.email} on {self.created_at}"

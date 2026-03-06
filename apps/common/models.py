from django.db import models
from tinymce.models import HTMLField

from apps.accounts.models import User


class PrivacyPolicy(models.Model):
    content = HTMLField()

    class Meta:
        verbose_name_plural = "Privacy Policy"

    def __str__(self):
        return "Privacy Policy"


class TermsConditions(models.Model):
    content = HTMLField()

    class Meta:
        verbose_name_plural = "Terms & Conditions"

    def __str__(self):
        return "Terms & Conditions"


class GardenProject(models.Model):
    """A user's garden project with name and design preferences."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="garden_projects"
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class GardenPhoto(models.Model):
    """Photo of a garden space for AI analysis."""

    QUALITY_CHOICES = [
        ("good", "Good"),
        ("poor", "Poor"),
        ("pending", "Pending Analysis"),
    ]

    project = models.OneToOneField(
        GardenProject, on_delete=models.CASCADE, related_name="garden_photo"
    )
    image = models.ImageField(upload_to="garden_photos/")
    quality_status = models.CharField(
        max_length=20, choices=QUALITY_CHOICES, default="pending"
    )
    quality_score = models.IntegerField(default=0, help_text="Quality score from 0-100")
    quality_issues = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.project.name}"


class GardenPreference(models.Model):
    """User preferences for garden design."""

    SUNLIGHT_CHOICES = [
        ("full_sun", "Full Sun (6+ hours)"),
        ("partial_sun", "Partial Sun (3-6 hours)"),
        ("full_shade", "Full Shade (<3 hours)"),
    ]

    SOIL_CHOICES = [
        ("sandy", "Sandy"),
        ("clay", "Clay"),
        ("loam", "Loam"),
        ("not_sure", "Not Sure"),
    ]

    GARDEN_TYPE_CHOICES = [
        ("flower", "Flower Garden"),
        ("vegetable", "Vegetable Garden"),
        ("herb", "Herb Garden"),
        ("mixed", "Mixed Garden"),
    ]

    project = models.OneToOneField(
        GardenProject, on_delete=models.CASCADE, related_name="garden_preference"
    )

    # Location
    location = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="City, zip code, or coordinates",
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Environmental factors
    sunlight = models.CharField(
        max_length=20, choices=SUNLIGHT_CHOICES, null=True, blank=True
    )
    soil_type = models.CharField(
        max_length=20, choices=SOIL_CHOICES, null=True, blank=True
    )

    # Garden design
    garden_type = models.CharField(
        max_length=20, choices=GARDEN_TYPE_CHOICES, null=True, blank=True
    )

    # Space measurements
    total_area_sq_ft = models.FloatField(
        null=True, blank=True, help_text="Total area in square feet"
    )
    height_ft = models.FloatField(null=True, blank=True, help_text="Height in feet")
    width_ft = models.FloatField(null=True, blank=True, help_text="Width in feet")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.project.name}"

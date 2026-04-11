from django.db import models

from apps.accounts.models import User
from apps.plants.models import Plant

# ─────────────────────────────────────────────────────────────────────────────
# Garden Photo
# ─────────────────────────────────────────────────────────────────────────────


class GardenPhoto(models.Model):
    """
    A photo of the user's garden space, uploaded for AI quality analysis.
    Created independently before (or without) a GardenProject.
    """

    QUALITY_CHOICES = [
        ("good", "Good"),
        ("poor", "Poor"),
        ("pending", "Pending Analysis"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="garden_photos",
        null=True,
        blank=True,
    )
    image = models.ImageField(upload_to="garden_photos/")
    quality_status = models.CharField(
        max_length=20, choices=QUALITY_CHOICES, default="pending"
    )
    quality_score = models.IntegerField(default=0, help_text="Quality score 0–100")
    quality_issues = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"GardenPhoto #{self.id}"


# ─────────────────────────────────────────────────────────────────────────────
# Garden Project  (main model — preferences live here)
# ─────────────────────────────────────────────────────────────────────────────


class GardenProject(models.Model):
    """
    A user's garden project.
    Preferences (sunlight, soil, type, colors) are stored directly on this model.
    Created in a single save when the user taps "Save" in the app.
    """

    SUNLIGHT_CHOICES = [
        ("full_sun", "Full Sun (6+ hours)"),
        ("partial_sun", "Partial Sun (3–6 hours)"),
        ("full_shade", "Full Shade (<3 hours)"),
    ]

    SOIL_CHOICES = [
        ("sandy", "Sandy"),
        ("clay", "Clay"),
        ("loam", "Loam"),
        ("not_sure", "Not Sure"),
    ]

    GARDEN_TYPE_CHOICES = [
        ("flower_garden", "Flower Garden"),
        ("vegetable_garden", "Vegetable Garden"),
        ("herb_garden", "Herb Garden"),
        ("mixed_garden", "Mixed Garden"),
    ]

    # Owner
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="garden_projects"
    )

    # Basic info
    name = models.CharField(max_length=255, default="My Garden")

    photo = models.ImageField(upload_to="garden_photos/", null=True, blank=True)

    # ── Location ─────────────────────────────────────────────────────────────
    location = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="City, zip code, or coordinates",
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # ── Environmental preferences ─────────────────────────────────────────────
    sunlight = models.CharField(
        max_length=20, choices=SUNLIGHT_CHOICES, null=True, blank=True
    )
    soil_type = models.CharField(
        max_length=20, choices=SOIL_CHOICES, null=True, blank=True
    )
    garden_type = models.CharField(
        max_length=20, choices=GARDEN_TYPE_CHOICES, null=True, blank=True
    )

    # Space measurements
    total_area_sq_ft = models.FloatField(
        null=True, blank=True, help_text="Total garden area in sq ft"
    )
    height_ft = models.FloatField(
        null=True, blank=True, help_text="Garden height in feet"
    )
    width_ft = models.FloatField(
        null=True, blank=True, help_text="Garden width in feet"
    )

    # ── AI Composition outputs ───────────────────────────────────────────────
    blended_image = models.ImageField(
        upload_to="garden_compositions/",
        null=True,
        blank=True,
        help_text="Final AI-blended garden image",
    )
    composite_image = models.ImageField(
        upload_to="garden_composites/",
        null=True,
        blank=True,
        help_text="Pre-AI composite (overlay) image",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user.username})"


# ─────────────────────────────────────────────────────────────────────────────
# Garden Plant placement
# ─────────────────────────────────────────────────────────────────────────────


class GardenPlant(models.Model):
    """
    A single plant placed inside a GardenProject at a specific position.
    x, y are relative (0.0–1.0) from the top-left of the garden image.
    """

    project = models.ForeignKey(
        GardenProject, on_delete=models.CASCADE, related_name="plants"
    )
    plant = models.ForeignKey(
        Plant, on_delete=models.CASCADE, related_name="garden_appearances"
    )

    x = models.FloatField(default=0.5, help_text="Relative X position (0.0–1.0)")
    y = models.FloatField(default=0.5, help_text="Relative Y position (0.0–1.0)")
    scale = models.FloatField(
        default=1.0, help_text="Scale factor (1.0 = natural size)"
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.plant.common_name} in {self.project.name}"

from django.db import models


class Plant(models.Model):
    common_name = models.CharField(max_length=255)
    scientific_name = models.CharField(max_length=255)  # JSON থেকে প্রথম এলিমেন্টটি নেবেন
    plant_type = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    # Images
    main_image_url = models.URLField(max_length=500, null=True, blank=True)

    # Growing conditions
    sunlight = models.CharField(max_length=100)
    water = models.CharField(max_length=255, null=True, blank=True)  # e.g., "Average"
    spacing = models.CharField(max_length=100, null=True, blank=True)
    growth_size = models.CharField(max_length=100, null=True, blank=True)
    season = models.CharField(max_length=100, null=True, blank=True)
    difficulty = models.CharField(
        max_length=100, null=True, blank=True
    )  # Mapping: care_level

    care_guide = models.TextField(null=True, blank=True)

    # Bloom Seasons
    bloom_spring = models.BooleanField(default=False)
    bloom_summer = models.BooleanField(default=False)
    bloom_fall = models.BooleanField(default=False)
    bloom_winter = models.BooleanField(default=False)

    # Tags & Shop
    shopping_link = models.URLField(max_length=500, null=True, blank=True)
    tags = models.TextField(help_text="Comma-separated tags", null=True, blank=True)

    # Extra Data (JSON থেকে যা যা রাখতে চান)
    family = models.CharField(max_length=100, null=True, blank=True)
    propagation = models.TextField(null=True, blank=True)  # Join the list with commas

    def __str__(self):
        return self.common_name

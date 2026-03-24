from django.db import models

from apps.accounts.models import User
from apps.gardens.models import GardenProject
from apps.plants.models import Plant


class GardenSchedule(models.Model):
    STATUS_CHOICES = [
        ("generated", "Generated"),
        ("archived", "Archived"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="garden_schedules"
    )
    project = models.ForeignKey(
        GardenProject,
        on_delete=models.CASCADE,
        related_name="schedules",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255, default="Garden Schedule")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="generated"
    )
    is_active = models.BooleanField(default=True)
    source_garden_data = models.JSONField(default=dict, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.title} - {self.user.email}"


class ScheduleMilestone(models.Model):
    schedule = models.ForeignKey(
        GardenSchedule, on_delete=models.CASCADE, related_name="milestones"
    )
    week = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["week", "display_order", "id"]

    def __str__(self):
        return f"Week {self.week}: {self.title}"


class ScheduleTask(models.Model):
    TYPE_CHOICES = [
        ("planting", "Planting"),
        ("watering", "Watering"),
        ("pruning", "Pruning"),
        ("fertilizing", "Fertilizing"),
        ("preparation", "Preparation"),
        ("other", "Other"),
    ]
    PRIORITY_CHOICES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("skipped", "Skipped"),
    ]

    milestone = models.ForeignKey(
        ScheduleMilestone, on_delete=models.CASCADE, related_name="tasks"
    )
    plant = models.ForeignKey(
        Plant,
        on_delete=models.SET_NULL,
        related_name="scheduled_tasks",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    task_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default="other")
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    duration_minutes = models.PositiveIntegerField(default=30)
    due_date = models.DateField(null=True, blank=True)
    tools_needed = models.JSONField(default=list, blank=True)
    materials = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "display_order", "id"]

    def __str__(self):
        return self.title

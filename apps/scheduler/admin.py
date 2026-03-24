from django.contrib import admin

from apps.scheduler.models import GardenSchedule, ScheduleMilestone, ScheduleTask


class ScheduleTaskInline(admin.TabularInline):
    model = ScheduleTask
    extra = 0


class ScheduleMilestoneInline(admin.TabularInline):
    model = ScheduleMilestone
    extra = 0


@admin.register(GardenSchedule)
class GardenScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "user",
        "project",
        "status",
        "is_active",
        "generated_at",
    )
    list_filter = ("status", "is_active", "generated_at")
    search_fields = ("title", "user__email", "project__name")
    inlines = [ScheduleMilestoneInline]


@admin.register(ScheduleMilestone)
class ScheduleMilestoneAdmin(admin.ModelAdmin):
    list_display = ("id", "schedule", "week", "title", "start_date", "end_date")
    search_fields = ("title", "schedule__title")
    list_filter = ("week",)
    inlines = [ScheduleTaskInline]


@admin.register(ScheduleTask)
class ScheduleTaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "milestone",
        "task_type",
        "priority",
        "status",
        "due_date",
    )
    search_fields = ("title", "milestone__title", "milestone__schedule__title")
    list_filter = ("task_type", "priority", "status")

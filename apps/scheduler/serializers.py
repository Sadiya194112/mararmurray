from django.utils import timezone
from rest_framework import serializers

from apps.scheduler.models import GardenSchedule, ScheduleMilestone, ScheduleTask


class ScheduleRequestSerializer(serializers.Serializer):
    project_id = serializers.IntegerField(required=False)
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    garden_data = serializers.DictField(required=False)

    def validate(self, attrs):
        incoming = attrs.get("garden_data")
        if incoming is None:
            incoming = {
                key: value
                for key, value in self.initial_data.items()
                if key not in {"project_id", "title"}
            }

        if not incoming and not attrs.get("project_id"):
            raise serializers.ValidationError(
                "Either project_id or garden_data must be provided."
            )

        if not incoming and attrs.get("project_id"):
            attrs["garden_data"] = None
            return attrs

        if not isinstance(incoming, dict):
            raise serializers.ValidationError(
                {"garden_data": "Garden data must be a JSON object."}
            )

        if not incoming.get("plants") or not isinstance(incoming.get("plants"), list):
            raise serializers.ValidationError(
                {"plants": "A non-empty plants array is required in garden data."}
            )

        attrs["garden_data"] = incoming
        return attrs


class NotificationRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    schedule = serializers.JSONField(required=False)
    recipients = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )


class ScheduleTaskSummarySerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="get_task_type_display")
    priority = serializers.CharField(source="get_priority_display")
    status = serializers.CharField(source="get_status_display")
    plant_name = serializers.SerializerMethodField()
    plant_image = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleTask
        fields = [
            "id",
            "title",
            "type",
            "priority",
            "status",
            "duration_minutes",
            "due_date",
            "plant_name",
            "plant_image",
        ]

    def get_plant_name(self, obj):
        return obj.plant.common_name if obj.plant else None

    def get_plant_image(self, obj):
        request = self.context.get("request")
        if not obj.plant:
            return None
        if obj.plant.image and request:
            return request.build_absolute_uri(obj.plant.image.url)
        return obj.plant.main_image_url


class ScheduleTaskDetailSerializer(ScheduleTaskSummarySerializer):
    tools_needed = serializers.ListField(child=serializers.CharField(), read_only=True)
    materials = serializers.ListField(child=serializers.CharField(), read_only=True)
    notes = serializers.CharField()
    milestone = serializers.SerializerMethodField()

    class Meta(ScheduleTaskSummarySerializer.Meta):
        fields = ScheduleTaskSummarySerializer.Meta.fields + [
            "tools_needed",
            "materials",
            "notes",
            "milestone",
        ]

    def get_milestone(self, obj):
        return {
            "id": obj.milestone.id,
            "week": obj.milestone.week,
            "title": obj.milestone.title,
            "start_date": obj.milestone.start_date,
            "end_date": obj.milestone.end_date,
        }


class ScheduleMilestoneListSerializer(serializers.ModelSerializer):
    task_count = serializers.SerializerMethodField()
    completed_task_count = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleMilestone
        fields = [
            "id",
            "week",
            "title",
            "description",
            "start_date",
            "end_date",
            "task_count",
            "completed_task_count",
        ]

    def get_task_count(self, obj):
        return obj.tasks.count()

    def get_completed_task_count(self, obj):
        return obj.tasks.filter(status="completed").count()


class ScheduleMilestoneDetailSerializer(ScheduleMilestoneListSerializer):
    tasks = ScheduleTaskSummarySerializer(many=True, read_only=True)

    class Meta(ScheduleMilestoneListSerializer.Meta):
        fields = ScheduleMilestoneListSerializer.Meta.fields + ["tasks"]


class UpcomingTaskSerializer(serializers.ModelSerializer):
    """Flat serializer for the Upcoming Tasks list screen."""

    project_name = serializers.SerializerMethodField()
    plant_image = serializers.SerializerMethodField()
    plant_name = serializers.SerializerMethodField()
    due_label = serializers.SerializerMethodField()
    task_type = serializers.CharField(source="get_task_type_display")
    priority = serializers.CharField(source="get_priority_display")
    task_status = serializers.CharField(source="get_status_display")

    class Meta:
        model = ScheduleTask
        fields = [
            "id",
            "title",
            "task_type",
            "priority",
            "task_status",
            "duration_minutes",
            "due_date",
            "due_label",
            "project_name",
            "plant_name",
            "plant_image",
        ]

    def get_project_name(self, obj):
        try:
            return obj.milestone.schedule.project.name
        except AttributeError:
            return obj.milestone.schedule.title

    def get_plant_name(self, obj):
        return obj.plant.common_name if obj.plant else None

    def get_plant_image(self, obj):
        request = self.context.get("request")
        if not obj.plant:
            return None
        if obj.plant.image and request:
            return request.build_absolute_uri(obj.plant.image.url)
        return obj.plant.main_image_url

    def get_due_label(self, obj):
        if not obj.due_date:
            return None
        today = timezone.now().date()
        delta = (obj.due_date - today).days
        if delta == 0:
            return "Today"
        if delta == 1:
            return "Tomorrow"
        if delta > 1:
            return obj.due_date.strftime("%b %d")
        return "Overdue"


class GardenScheduleSerializer(serializers.ModelSerializer):
    milestones = ScheduleMilestoneListSerializer(many=True, read_only=True)

    class Meta:
        model = GardenSchedule
        fields = [
            "id",
            "title",
            "status",
            "is_active",
            "generated_at",
            "updated_at",
            "milestones",
        ]

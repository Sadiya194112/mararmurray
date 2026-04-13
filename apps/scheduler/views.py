import logging
from datetime import datetime

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from ai_plant_engine.plant_scheduler.engine import PlantScheduler
from apps.gardens.models import GardenProject
from apps.scheduler.models import GardenSchedule, ScheduleMilestone, ScheduleTask
from apps.scheduler.serializers import (
    GardenScheduleSerializer,
    NotificationRequestSerializer,
    ScheduleMilestoneDetailSerializer,
    ScheduleRequestSerializer,
    ScheduleTaskDetailSerializer,
    ScheduleTaskSummarySerializer,
    UpcomingTaskSerializer,
)
from apps.scheduler.services import (
    build_garden_data_from_project,
    save_generated_schedule,
)

logger = logging.getLogger(__name__)


@swagger_auto_schema(method="get", tags=["6. Scheduler"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def user_home_stats(request):
    """
    Returns 3 counts for the logged-in user's home screen:
    - projects:  total garden projects created by the user
    - tasks_today: tasks due today across all the user's active schedules
    - plants: total plant slots placed across all the user's projects
    """
    from apps.gardens.models import GardenPlant

    today = timezone.now().date()
    user = request.user

    project_count = GardenProject.objects.filter(user=user).count()

    tasks_today = ScheduleTask.objects.filter(
        milestone__schedule__user=user,
        milestone__schedule__is_active=True,
        due_date=today,
    ).count()

    plants_count = GardenPlant.objects.filter(project__user=user).count()

    return Response(
        {
            "projects": project_count,
            "tasks_today": tasks_today,
            "plants": plants_count,
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["6. Scheduler"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def upcoming_tasks(request):
    """
    Returns the logged-in user's upcoming pending tasks ordered by due date.
    Shows tasks from today onwards across all active schedules.
    Optional query param: limit (default 10)
    """
    today = timezone.now().date()
    try:
        limit = min(max(1, int(request.query_params.get("limit", 10))), 50)
    except (TypeError, ValueError):
        return Response(
            {"error": "limit must be an integer"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    tasks = (
        ScheduleTask.objects.select_related("plant", "milestone__schedule__project")
        .filter(
            milestone__schedule__user=request.user,
            milestone__schedule__is_active=True,
            status="pending",
            due_date__gte=today,
        )
        .order_by("due_date", "display_order", "id")[:limit]
    )

    return Response(
        UpcomingTaskSerializer(tasks, many=True, context={"request": request}).data,
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="post", tags=["6. Scheduler"])
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def generate_schedule(request):
    """
    Generate a weekly schedule from full garden JSON data.
    Accepts either:
    1) {"garden_data": {...}}
    2) raw garden JSON object in request body
    """
    serializer = ScheduleRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        project = None
        project_id = serializer.validated_data.get("project_id")
        garden_data = serializer.validated_data.get("garden_data")

        if project_id:
            project = get_object_or_404(
                GardenProject.objects.prefetch_related("plants__plant"),
                id=project_id,
                user=request.user,
            )

        if garden_data is None and project:
            garden_data = build_garden_data_from_project(project)

        scheduler = PlantScheduler()
        generated_payload = scheduler.generate_schedule(garden_data)
        saved_schedule = save_generated_schedule(
            user=request.user,
            project=project,
            title=serializer.validated_data.get("title"),
            garden_data=garden_data,
            schedule_data=generated_payload,
        )
        print("Garden Data: ", garden_data)  # Debug log
        print("Generated Schedule: ", generated_payload)  # Debug log
        print("Saved Schedule: ", saved_schedule)  # Debug log
        return Response(
            {
                "message": "Schedule generated successfully",
                "schedule": GardenScheduleSerializer(saved_schedule).data,
                "raw_schedule": generated_payload,
            },
            status=status.HTTP_200_OK,
        )
    except Exception as exc:
        logger.error("Schedule generation failed: %s", exc)
        return Response(
            {
                "error": "Failed to generate schedule",
                "details": str(exc),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@swagger_auto_schema(method="post", tags=["6. Scheduler"])
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_notification(request):
    """
    Notification API scaffold for schedule reminders.
    You can extend this endpoint with your preferred scheduler/notification logic.
    """
    serializer = NotificationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    payload = serializer.validated_data
    return Response(
        {
            "message": "Notification payload received",
            "notification": {
                "title": payload["title"],
                "message": payload["message"],
                "recipients": payload.get("recipients", []),
            },
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["6. Scheduler"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def project_timeline(request, project_id):
    project = get_object_or_404(GardenProject, id=project_id, user=request.user)
    schedule = get_object_or_404(
        GardenSchedule.objects.filter(project=project, is_active=True)
        .prefetch_related(
            Prefetch(
                "milestones",
                queryset=ScheduleMilestone.objects.prefetch_related("tasks__plant"),
            )
        )
        .order_by("-generated_at")
    )

    next_task = (
        ScheduleTask.objects.select_related("plant", "milestone")
        .filter(milestone__schedule=schedule, status="pending")
        .order_by("due_date", "display_order", "id")
        .first()
    )

    milestones = schedule.milestones.all()
    return Response(
        {
            "schedule": {
                "id": schedule.id,
                "title": schedule.title,
                "generated_at": schedule.generated_at,
            },
            "project": {
                "id": project.id,
                "name": project.name,
                "location": project.location,
                "photo": request.build_absolute_uri(project.photo.url)
                if project.photo
                else None,
            },
            "next_task": ScheduleTaskSummarySerializer(
                next_task, context={"request": request}
            ).data
            if next_task
            else None,
            "upcoming_milestones": ScheduleMilestoneDetailSerializer(
                milestones, many=True, context={"request": request}
            ).data,
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["6. Scheduler"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def milestone_detail(request, milestone_id):
    milestone = get_object_or_404(
        ScheduleMilestone.objects.select_related("schedule__project").prefetch_related(
            "tasks__plant"
        ),
        id=milestone_id,
        schedule__user=request.user,
    )
    return Response(
        ScheduleMilestoneDetailSerializer(milestone, context={"request": request}).data,
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["6. Scheduler"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def task_detail(request, task_id):
    task = get_object_or_404(
        ScheduleTask.objects.select_related("plant", "milestone__schedule__project"),
        id=task_id,
        milestone__schedule__user=request.user,
    )
    return Response(
        ScheduleTaskDetailSerializer(task, context={"request": request}).data,
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="patch", tags=["6. Scheduler"])
@api_view(["PATCH"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_task_status(request, task_id):
    task = get_object_or_404(
        ScheduleTask,
        id=task_id,
        milestone__schedule__user=request.user,
    )

    new_status = str(request.data.get("status", "")).strip().lower()
    if new_status not in {"pending", "completed", "skipped"}:
        return Response(
            {"error": "status must be one of: pending, completed, skipped"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    task.status = new_status
    task.completed_at = timezone.now() if new_status == "completed" else None
    task.save(update_fields=["status", "completed_at", "updated_at"])

    return Response(
        {
            "message": "Task status updated successfully",
            "task": ScheduleTaskDetailSerializer(
                task, context={"request": request}
            ).data,
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="delete", tags=["6. Scheduler"])
@api_view(["DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def delete_task(request, task_id):
    task = get_object_or_404(
        ScheduleTask,
        id=task_id,
        milestone__schedule__user=request.user,
    )
    task.delete()
    return Response(
        {"message": "Task deleted successfully"},
        status=status.HTTP_204_NO_CONTENT,
    )


@swagger_auto_schema(method="get", tags=["6. Scheduler"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def project_calendar(request, project_id):
    project = get_object_or_404(GardenProject, id=project_id, user=request.user)
    schedule = get_object_or_404(
        GardenSchedule,
        project=project,
        is_active=True,
    )

    year = int(request.query_params.get("year", timezone.now().year))
    month = int(request.query_params.get("month", timezone.now().month))

    tasks = (
        ScheduleTask.objects.select_related("milestone")
        .filter(
            milestone__schedule=schedule,
            due_date__year=year,
            due_date__month=month,
        )
        .order_by("due_date", "display_order", "id")
    )

    grouped = {}
    for task in tasks:
        if not task.due_date:
            continue
        date_key = task.due_date.isoformat()
        grouped.setdefault(date_key, []).append(
            {
                "id": task.id,
                "title": task.title,
                "type": task.get_task_type_display(),
                "status": task.get_status_display(),
                "priority": task.get_priority_display(),
            }
        )

    return Response(
        {
            "project_id": project.id,
            "schedule_id": schedule.id,
            "year": year,
            "month": month,
            "days": [
                {
                    "date": date_key,
                    "task_count": len(items),
                    "tasks": items,
                }
                for date_key, items in sorted(grouped.items())
            ],
            "legend": [
                {"type": "Planting", "color": "green"},
                {"type": "Watering", "color": "blue"},
                {"type": "Pruning", "color": "orange"},
                {"type": "Fertilizing", "color": "purple"},
                {"type": "Preparation", "color": "olive"},
            ],
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["6. Scheduler"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def project_calendar_day(request, project_id):
    project = get_object_or_404(GardenProject, id=project_id, user=request.user)
    schedule = get_object_or_404(
        GardenSchedule,
        project=project,
        is_active=True,
    )

    selected_date = request.query_params.get("date")
    if not selected_date:
        return Response(
            {"error": "date query param is required. Example: 2026-03-24"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    tasks = ScheduleTask.objects.select_related("plant", "milestone").filter(
        milestone__schedule=schedule,
        due_date=selected_date,
    )

    return Response(
        {
            "project_id": project.id,
            "schedule_id": schedule.id,
            "date": selected_date,
            "tasks": ScheduleTaskSummarySerializer(
                tasks, many=True, context={"request": request}
            ).data,
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["6. Scheduler"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def tasks_by_date(request, date):
    """
    Returns detailed tasks for the logged-in user on a given date.
    Date must be passed as a URL param in YYYY-MM-DD format.
    """
    try:
        selected_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return Response(
            {"error": "Invalid date format. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    tasks = (
        ScheduleTask.objects.select_related("plant", "milestone__schedule__project")
        .filter(
            milestone__schedule__user=request.user,
            milestone__schedule__is_active=True,
            due_date=selected_date,
        )
        .order_by("display_order", "id")
    )

    return Response(
        {
            "date": selected_date.isoformat(),
            "task_count": tasks.count(),
            "tasks": ScheduleTaskDetailSerializer(
                tasks, many=True, context={"request": request}
            ).data,
        },
        status=status.HTTP_200_OK,
    )

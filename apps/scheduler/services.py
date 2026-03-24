from datetime import datetime

from django.db import transaction

from apps.gardens.models import GardenProject
from apps.scheduler.models import GardenSchedule, ScheduleMilestone, ScheduleTask

KNOWN_TASK_TYPES = {"planting", "watering", "pruning", "fertilizing", "preparation"}
KNOWN_PRIORITIES = {"high", "medium", "low"}
KNOWN_STATUSES = {"pending", "completed", "skipped"}


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return value


def _normalize_choice(value, allowed_values, default_value):
    if not value:
        return default_value
    normalized = str(value).strip().lower()
    return normalized if normalized in allowed_values else default_value


def build_garden_data_from_project(project: GardenProject):
    plants = []
    for placed_plant in project.plants.select_related("plant").all():
        plant = placed_plant.plant
        plants.append(
            {
                "id": plant.id,
                "name": plant.common_name,
                "scientific_name": plant.scientific_name,
                "spacing": plant.spacing or "",
                "sunlight": plant.sunlight or "",
                "water": plant.water or "",
                "soil_type": plant.soil_type or "",
                "season": plant.season or "",
                "care_guide": plant.care_guide or "",
            }
        )

    return {
        "name": project.name,
        "location": project.location,
        "soil_type": project.soil_type,
        "sunlight": project.sunlight,
        "garden_type": project.garden_type,
        "area_sqft": project.total_area_sq_ft,
        "plants": plants,
    }


def _find_matching_plant(project, task_title, notes):
    if not project:
        return None

    haystack = f"{task_title} {notes}".lower()
    for placed_plant in project.plants.select_related("plant").all():
        plant = placed_plant.plant
        if plant.common_name and plant.common_name.lower() in haystack:
            return plant
    return None


@transaction.atomic
def save_generated_schedule(
    *, user, project=None, title=None, garden_data=None, schedule_data=None
):
    if project:
        project.schedules.filter(is_active=True).update(
            is_active=False, status="archived"
        )

    schedule = GardenSchedule.objects.create(
        user=user,
        project=project,
        title=title
        or (project.name if project else garden_data.get("name") or "Garden Schedule"),
        source_garden_data=garden_data or {},
        raw_response=schedule_data or {},
        status="generated",
        is_active=True,
    )

    for milestone_index, milestone_payload in enumerate(
        schedule_data.get("milestones", []), start=1
    ):
        milestone = ScheduleMilestone.objects.create(
            schedule=schedule,
            week=milestone_payload.get("week") or milestone_index,
            title=milestone_payload.get("title") or f"Week {milestone_index}",
            description=milestone_payload.get("description") or "",
            start_date=_parse_date(milestone_payload.get("start_date")),
            end_date=_parse_date(milestone_payload.get("end_date")),
            display_order=milestone_index,
        )

        for task_index, task_payload in enumerate(
            milestone_payload.get("tasks", []), start=1
        ):
            notes = task_payload.get("notes") or ""
            ScheduleTask.objects.create(
                milestone=milestone,
                plant=_find_matching_plant(
                    project, task_payload.get("title") or "", notes
                ),
                title=task_payload.get("title") or f"Task {task_index}",
                task_type=_normalize_choice(
                    task_payload.get("type"), KNOWN_TASK_TYPES, "other"
                ),
                priority=_normalize_choice(
                    task_payload.get("priority"), KNOWN_PRIORITIES, "medium"
                ),
                status=_normalize_choice(
                    task_payload.get("status"), KNOWN_STATUSES, "pending"
                ),
                duration_minutes=task_payload.get("duration_minutes") or 30,
                due_date=_parse_date(task_payload.get("due_date"))
                or _parse_date(milestone_payload.get("start_date")),
                tools_needed=task_payload.get("tools_needed") or [],
                materials=task_payload.get("materials") or [],
                notes=notes,
                display_order=task_index,
            )

    return schedule

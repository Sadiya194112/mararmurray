from django.urls import path

from apps.scheduler.views import (
    create_notification,
    delete_task,
    generate_schedule,
    milestone_detail,
    project_calendar,
    project_calendar_day,
    project_timeline,
    task_detail,
    tasks_by_date,
    upcoming_tasks,
    update_task_status,
    user_home_stats,
)

urlpatterns = [
    path("home/stats/", user_home_stats, name="user-home-stats"),
    path("home/upcoming-tasks/", upcoming_tasks, name="upcoming-tasks"),
    path("generate/", generate_schedule, name="generate-schedule"),
    path("notifications/", create_notification, name="create-notification"),
    path(
        "projects/<int:project_id>/timeline/", project_timeline, name="project-timeline"
    ),
    path(
        "projects/<int:project_id>/calendar/", project_calendar, name="project-calendar"
    ),
    path(
        "projects/<int:project_id>/calendar/day/",
        project_calendar_day,
        name="project-calendar-day",
    ),
    path("milestones/<int:milestone_id>/", milestone_detail, name="milestone-detail"),
    path("tasks/<int:task_id>/", task_detail, name="task-detail"),
    path("tasks/date/<str:date>/", tasks_by_date, name="tasks-by-date"),
    path("tasks/<int:task_id>/status/", update_task_status, name="update-task-status"),
    path("tasks/<int:task_id>/delete/", delete_task, name="delete-task"),
]

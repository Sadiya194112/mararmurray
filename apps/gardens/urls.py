from django.urls import path
from apps.gardens.views import (
    create_garden_project,
    upload_garden_photo,
    list_garden_projects,
    garden_project_detail,
    compose_garden_and_save
)

urlpatterns = [
    # Project APIs
    path("projects/", list_garden_projects, name="list-garden-projects"),
    path("projects/create/", create_garden_project, name="create-garden-project"),
    path("projects/<int:pk>/", garden_project_detail, name="garden-project-detail"),
    
    # Photo standalone APIs
    path("photos/upload/", upload_garden_photo, name="upload-garden-photo"),

    path("compose/garden/", compose_garden_and_save, name="compose-garden"),
]

from django.urls import path

from apps.gardens.views import (
    compose_garden_and_save,
    download_blended_image,
    create_garden_project,
    garden_project_action,
    list_garden_projects,
    retrieve_garden_project_with_plants,
    upload_garden_photo,
)

urlpatterns = [
    # Project APIs
    path("projects/", list_garden_projects, name="list-garden-projects"),
    path("projects/create/", create_garden_project, name="create-garden-project"),
    path(
        "projects/<int:project_id>/detail/",
        retrieve_garden_project_with_plants,
        name="garden-project-detail-with-plants",
    ),
    path(
        "projects/<int:project_id>/",
        garden_project_action,
        name="garden-project-detail",
    ),
    path(
        "projects/<int:project_id>/download-blended/",
        download_blended_image,
        name="download-blended-image",
    ),
    # Photo standalone APIs
    path("photos/upload/", upload_garden_photo, name="upload-garden-photo"),
    path("compose/garden/", compose_garden_and_save, name="compose-garden"),
]

from django.urls import path

from apps.plants.views import (
    add_plant,
    delete_plant_image,
    get_plant_image,
    plant_detail_view,
    sync_plants_batch_view,
    upload_plant_image,
)

urlpatterns = [
    # 4. Plant APIs
    # 4.1 Sync Plants Batch
    path("sync-plants-action/", sync_plants_batch_view, name="sync-plants-url"),
    # 4.2 Get Plant Detail
    path("plant/detail/<int:plant_id>/", plant_detail_view, name="plant-detail"),
    # 4.3 Add Plant
    path("add/plant/", add_plant, name="add-plant"),
    # 4.4 Upload Plant Image
    path(
        "plant/<int:plant_id>/image/upload/",
        upload_plant_image,
        name="upload-plant-image",
    ),
    # 4.5 Get Plant Image
    path("plant/<int:plant_id>/image/", get_plant_image, name="get-plant-image"),
    # 4.6 Delete Plant Image
    path(
        "plant/<int:plant_id>/image/delete/",
        delete_plant_image,
        name="delete-plant-image",
    ),
]

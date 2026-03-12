from django.urls import path

from apps.plants.views import (
    add_plant,
    plants,
    delete_plant_image,
    get_plant_image,
    plant_detail,
    upload_plant_image,
)

urlpatterns = [
    # 4. Plant APIs
    path("", plants, name='plants'),
    path("plant/detail/<int:plant_id>/", plant_detail, name="plant-detail"),
    
    # For Admin
    path("add/plant/", add_plant, name="add-plant"),
    path(
        "plant/<int:plant_id>/image/upload/",
        upload_plant_image,
        name="upload-plant-image",
    ),
    path("plant/<int:plant_id>/image/", get_plant_image, name="get-plant-image"),
    path(
        "plant/<int:plant_id>/image/delete/",
        delete_plant_image,
        name="delete-plant-image",
    ),



]

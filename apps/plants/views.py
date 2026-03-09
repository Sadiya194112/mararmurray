from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.plants.models import Plant
from apps.plants.serializers import PlantSerializer
from apps.plants.services import PlantSyncService

# ============== Plant APIs ==============


@swagger_auto_schema(method="post", tags=["4. Plants"])
@api_view(["POST"])
def sync_plants_batch_view(request):
    # রিকোয়েস্ট থেকে start_id নিন, না থাকলে ডিফল্ট ১
    start_id = int(request.data.get("start_id", 1))

    count, next_start = PlantSyncService.sync_all_plants(
        start_id=start_id, batch_size=100
    )

    return Response(
        {
            "message": f"{count} plants synced successfully.",
            "next_start_id": next_start + 1,
        }
    )


@swagger_auto_schema(method="get", tags=["4. Plants"])
@api_view(["GET"])
def plant_detail_view(request, plant_id):
    """Return serialized details for a single plant.

    The URL passes the plant's primary key as ``pk``. The view is intentionally
    open so that anyone (authenticated or not) can inspect plant data. If the
    object does not exist we return a 404 response.
    """

    plant = get_object_or_404(Plant, pk=plant_id)
    serializer = PlantSerializer(plant)
    return Response(serializer.data)


@swagger_auto_schema(method="post", tags=["4. Plants"])
@api_view(["POST"])
@permission_classes([IsAdminUser])
@authentication_classes([JWTAuthentication])
def add_plant(request):
    serializer = PlantSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "Plant added successfully!", "data": serializer.data}
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============== Plant Image APIs ==============


@swagger_auto_schema(method="post", tags=["4. Plants"])
@api_view(["POST"])
def upload_plant_image(request, plant_id):
    """4.4 Upload plant image"""
    plant = get_object_or_404(Plant, id=plant_id)
    image_file = request.FILES.get("image")
    if not image_file:
        return Response(
            {"message": "No image file provided"}, status=status.HTTP_400_BAD_REQUEST
        )
    plant.image = image_file
    plant.save()
    return Response(
        {
            "message": "Plant image uploaded successfully",
            "image_url": plant.image.url if plant.image else None,
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["4. Plants"])
@api_view(["GET"])
def get_plant_image(request, plant_id):
    """4.5 Get plant image"""
    plant = get_object_or_404(Plant, id=plant_id)
    if plant.image:
        return Response({"image_url": plant.image.url}, status=status.HTTP_200_OK)
    return Response({"message": "No plant image"}, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(method="delete", tags=["4. Plants"])
@api_view(["DELETE"])
def delete_plant_image(request, plant_id):
    """4.6 Delete plant image"""
    plant = get_object_or_404(Plant, id=plant_id)
    if plant.image:
        plant.image.delete()
        plant.image = None
        plant.save()
        return Response(
            {"message": "Plant image deleted successfully"}, status=status.HTTP_200_OK
        )
    return Response(
        {"message": "No plant image to delete"}, status=status.HTTP_404_NOT_FOUND
    )

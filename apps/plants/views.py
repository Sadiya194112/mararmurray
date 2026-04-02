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

# ============== Plant APIs ==============


SUNLIGHT_CHOICES = ["full_sun", "partial_sun", "full_shade"]

SOIL_TYPE_CHOICES = ["sandy", "clay", "loam", "not_sure"]

GARDEN_TYPE_CHOICES = [
    "flower_garden",
    "vegetable_garden",
    "herb_garden",
    "mixed_garden",
]


@swagger_auto_schema(method="get", tags=["4. Plants"])
@api_view(["GET"])
def plants(request):
    """
    | Param         | Valid values |
    |---|---|
    | `sunlight`    | `full_sun` · `partial_sun` · `full_shade` |
    | `soil_type`   | `sandy` · `clay` · `loam` · `not_sure` |
    | `garden_type` | `flower_garden` · `vegetable_garden` · `herb_garden` · `mixed_garden` |
    | `color`       | Any string (case-insensitive contains match) |
    | `page`        | Page number (default: 1) |
    | `limit`       | Items per page (default: 10, max: 50) |
    """

    sunlight = request.query_params.get("sunlight")
    soil_type = request.query_params.get("soil_type")
    garden_type = request.query_params.get("garden_type")
    color = request.query_params.get("color")

    errors = {}
    if sunlight and sunlight not in SUNLIGHT_CHOICES:
        errors["sunlight"] = f"Invalid choice. Must be one of: {SUNLIGHT_CHOICES}"
    if soil_type and soil_type not in SOIL_TYPE_CHOICES:
        errors["soil_type"] = f"Invalid choice. Must be one of: {SOIL_TYPE_CHOICES}"
    if garden_type and garden_type not in GARDEN_TYPE_CHOICES:
        errors["garden_type"] = f"Invalid choice. Must be one of: {GARDEN_TYPE_CHOICES}"
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    queryset = Plant.objects.all().order_by("id")

    if sunlight:
        queryset = queryset.filter(sunlight=sunlight)
    if soil_type:
        queryset = queryset.filter(soil_type=soil_type)
    if garden_type:
        queryset = queryset.filter(garden_type=garden_type)

    if color:
        queryset = queryset.filter(color__icontains=color)

    try:
        page = max(1, int(request.query_params.get("page", 1)))
        limit = max(1, min(50, int(request.query_params.get("limit", 10))))
    except (ValueError, TypeError):
        return Response(
            {"error": "page and limit must be integers."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    total = queryset.count()
    total_pages = (total + limit - 1) // limit if total else 1
    offset = (page - 1) * limit
    page_qs = queryset[offset : offset + limit]

    plants_data = []
    for plant in page_qs:
        image_url = None
        if plant.image:
            image_url = request.build_absolute_uri(plant.image.url)
        elif plant.main_image_url:
            image_url = plant.main_image_url

        plants_data.append(
            {
                "id": plant.pk,
                "name": plant.common_name,
                "scientific_name": plant.scientific_name or "",
                "plant_type": plant.plant_type or "",
                "color": plant.color or "",
                "spacing": plant.spacing or "",  # e.g. "18-24 inches"
                "sunlight": plant.sunlight or "",  # e.g. "full_sun"
                "water": plant.water or "",  # e.g. "High water"
                "soil_type": plant.soil_type or "",  # e.g. "sandy"
                "garden_type": plant.garden_type or "",  # e.g. "flower_garden"
                "image": image_url,
            }
        )

    return Response(
        {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "plant": plants_data,
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["4. Plants"])
@api_view(["GET"])
def plant_detail(request, plant_id):
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


@swagger_auto_schema(method="patch", tags=["4. Plants"])
@api_view(["PATCH"])
@permission_classes([IsAdminUser])
@authentication_classes([JWTAuthentication])
def plant_edit(request, plant_id):
    plant = get_object_or_404(Plant, pk=plant_id)
    serializer = PlantSerializer(plant, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "Plant updated successfully!", "data": serializer.data}
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


@swagger_auto_schema(method="delete", tags=["4. Plants"])
@api_view(["DELETE"])
@permission_classes([IsAdminUser])
@authentication_classes([JWTAuthentication])
def delete_plant(request, plant_id):
    """4.3 Delete plant (Admin only)"""
    plant = get_object_or_404(Plant, id=plant_id)
    plant.delete()
    return Response(
        {"message": "Plant deleted successfully"}, status=status.HTTP_200_OK
    )

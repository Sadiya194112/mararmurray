import base64
import logging

from django.core.files.base import ContentFile
from django.http import FileResponse
from django.shortcuts import get_object_or_404
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

from apps.gardens.ai.main import analyze_image_quality
from apps.gardens.ai.pic_marge_used import create_garden_mockup
from apps.gardens.models import GardenPhoto, GardenPlant, GardenProject
from apps.gardens.serializers import (
    GardenPhotoSerializer,
    GardenProjectDetailSerializer,
    GardenProjectSerializer,
)
from apps.plants.models import Plant

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  1.  Garden Project Creation & Quality Check
# ─────────────────────────────────────────────


@swagger_auto_schema(method="post", tags=["1. Garden Projects"])
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_garden_project(request):
    serializer = GardenProjectSerializer(data=request.data)

    if serializer.is_valid():
        photo_id = request.data.get("photo_id")
        image_file = request.FILES.get("photo")

        # ১. যদি ইউজার আগে আপলোড করা কোনো photo_id পাঠায়
        if photo_id:
            try:
                garden_photo = GardenPhoto.objects.get(id=photo_id, user=request.user)
                # photo_id path ধরে নিচ্ছি যে quality আগেই upload_garden_photo তে চেক হয়েছে
                serializer.save(user=request.user, photo=garden_photo.image)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            except GardenPhoto.DoesNotExist:
                return Response(
                    {"error": "Photo ID not found"}, status=status.HTTP_404_NOT_FOUND
                )

        # ২. যদি ইউজার সরাসরি নতুন ফাইল আপলোড করে
        elif image_file:
            # অস্থায়ীভাবে সেভ করছি পাথ পাওয়ার জন্য
            temp_photo = GardenPhoto.objects.create(
                user=request.user,
                image=image_file,
                quality_status="pending",  # স্পষ্টভাবে বলে দিন
                quality_score=0,
            )
            try:
                quality_report = analyze_image_quality(temp_photo.image.path)
                if not quality_report.get("is_good_quality"):
                    return Response(
                        {
                            "status": "quality_warning",
                            "message": "Quality issues detected.",
                            "issues": quality_report.get("issues"),
                            "photo_id": temp_photo.id,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # কোয়ালিটি ভালো হলে এই ফাইলটি প্রজেক্টে যুক্ত করে দিন
                serializer.save(user=request.user, photo=temp_photo.image)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            except Exception as ai_err:
                logger.error(f"AI Check failed: {str(ai_err)}")
                # AI ফেইল করলে কি প্রজেক্ট সেভ হতে দেবেন? দিলে নিচের লাইনটি রাখুন:
                serializer.save(user=request.user, photo=image_file)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        # ৩. যদি কোনো ছবিই না থাকে (Optional Photo)
        else:
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────
#  2. Photo Upload (Standalone)
# ─────────────────────────────────────────────


@swagger_auto_schema(method="post", tags=["2. Garden Photo"])
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def upload_garden_photo(request):
    """
    Stand-alone photo upload and quality analysis.
    Returns a photo_id that can be used later in project creation.
    """
    serializer = GardenPhotoSerializer(data=request.data)
    if serializer.is_valid():
        photo = serializer.save(user=request.user)
        try:
            report = analyze_image_quality(photo.image.path)
            photo.quality_status = "good" if report.get("is_good_quality") else "poor"
            photo.quality_issues = report.get("issues", [])
            photo.save()
            return Response(
                {
                    "photo_id": photo.id,
                    "is_good_quality": report.get("is_good_quality"),
                    "issues": report.get("issues"),
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Standalone AI quality check failed: {str(e)}")
            return Response(
                {"photo_id": photo.id, "error": "AI check failed"},
                status=status.HTTP_201_CREATED,
            )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────
#  3. Garden Project Listing & Detail
# ─────────────────────────────────────────────


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def list_garden_projects(request):
    projects = GardenProject.objects.filter(user=request.user)
    serializer = GardenProjectSerializer(projects, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def retrieve_garden_project_with_plants(request, project_id):
    project = get_object_or_404(
        GardenProject.objects.prefetch_related("plants__plant"),
        id=project_id,
        user=request.user,
    )
    serializer = GardenProjectDetailSerializer(project, context={"request": request})
    return Response(serializer.data)


#
@api_view(["GET", "PATCH", "DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def garden_project_action(request, project_id):
    project = get_object_or_404(GardenProject, id=project_id, user=request.user)

    if request.method == "GET":
        serializer = GardenProjectSerializer(project)
        return Response(serializer.data)

    elif request.method == "PATCH":
        serializer = GardenProjectSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        project.delete()
        return Response(
            {"message": "Project deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )


# AI Blending and Composing


def _base64_to_file(data, name):
    """Base64 স্ট্রিং থেকে Django ফাইল অবজেক্টে রূপান্তর করার হেল্পার"""
    try:
        format, imgstr = data.split(";base64,") if ";base64," in data else (None, data)
        return ContentFile(base64.b64decode(imgstr), name=name)
    except Exception:
        return None


@swagger_auto_schema(method="post", tags=["3. Garden Project"])
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def compose_garden_and_save(request):
    data = request.data
    project_id = data.get("project_id")
    plants_input = data.get("plants", [])

    project = get_object_or_404(GardenProject, id=project_id, user=request.user)

    if not project.photo or not plants_input:
        return Response({"error": "Garden photo and plants are required."}, status=400)

    # HIGHLIGHT: পাথ এবং পজিশন ডাটা একসাথে গুছিয়ে নেওয়া
    plants_data_for_ai = []
    resolved_plants = []

    print("DEBUG: Processing plants_input ->", plants_input)
    for item in plants_input:
        plant_id = item.get("plant_id")
        print(f"DEBUG: Checking plant_id {plant_id}")
        try:
            plant = Plant.objects.get(id=plant_id)
            print(f"DEBUG: Found plant in DB -> {plant} (id={plant.id})")
            
            if plant.main_image_url:
                print(f"DEBUG: Plant {plant.id} has image -> {plant.main_image_url}")
                try:
                    plants_data_for_ai.append(
                        {
                            "path": plant.main_image_url,
                            "x": item["x"],
                            "y": item["y"],
                            "scale": item.get("scale", 1.0),
                        }
                    )
                    resolved_plants.append(
                        {
                            "instance": plant,
                            "x": item["x"],
                            "y": item["y"],
                            "scale": item.get("scale", 1.0),
                        }
                    )
                    print(f"DEBUG: Successfully added plant {plant.id}")
                except Exception as inner_e:
                    print(f"DEBUG: Error accessing plant data properties for {plant.id}: {inner_e}")
            else:
                print(f"DEBUG: Plant {plant.id} has NO main_image_url attached in DB.")
                
        except Plant.DoesNotExist:
            print(f"DEBUG: Plant.DoesNotExist for plant_id {plant_id}")
            continue
        except Exception as e:
            print(f"DEBUG: Unexpected error for plant_id {plant_id} -> {e}")
            continue

    print("DEBUG: Final Plants data for ai: ", plants_data_for_ai)
    
    if not plants_data_for_ai:
        return Response(
            {"error": "Selected plants do not have images in the database. AI cannot render without plant photos."}, 
            status=400
        )

    try:
        # ৩. কলিং এআই মেকার
        ai_generated_file = create_garden_mockup(
            background_path=project.photo.path,
            plants_data=plants_data_for_ai,  # HIGHLIGHT: এখন আমরা পজিশন ডাটাও পাঠাচ্ছি
        )

        if ai_generated_file:
            project.blended_image.save(
                f"garden_{project.id}_ai.jpg", ai_generated_file, save=False
            )
        else:
            return Response({"error": "AI response was empty."}, status=500)

    except Exception as e:
        return Response({"error": f"AI Processing failed: {str(e)}"}, status=500)

    project.save(update_fields=["blended_image", "updated_at"])

    GardenPlant.objects.filter(project=project).delete()
    for p in resolved_plants:
        GardenPlant.objects.create(
            project=project, plant=p["instance"], x=p["x"], y=p["y"], scale=p["scale"]
        )

    serializer = GardenProjectSerializer(project, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method="get", tags=["3. Garden Project"])
@api_view(["GET"])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
def download_blended_image(request, project_id):
    project = get_object_or_404(GardenProject, id=project_id, user=request.user)

    if not project.blended_image:
        return Response(
            {"error": "Blended image not found."}, 
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        response = FileResponse(project.blended_image.open("rb"), content_type="image/jpeg", as_attachment=True)
        response["Content-Disposition"] = f'attachment; filename="blended_image_{project.id}.jpg"'
        return response
    except Exception as e:
        return Response(
            {"error": f"Failed to download image: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

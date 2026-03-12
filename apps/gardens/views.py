import logging
import os
import base64
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.gardens.models import GardenPhoto, GardenProject
from apps.gardens.serializers import GardenProjectSerializer, GardenPhotoSerializer
from apps.gardens.ai.main import analyze_image_quality

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  1. Garden Project Creation & Quality Check
# ─────────────────────────────────────────────

@swagger_auto_schema(method="post", tags=["1. Garden Projects"])
@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_garden_project(request):
    serializer = GardenProjectSerializer(data=request.data)
    
    if serializer.is_valid():
        photo_id = request.data.get('photo_id')
        image_file = request.FILES.get('photo')
        
        # ১. যদি ইউজার আগে আপলোড করা কোনো photo_id পাঠায়
        if photo_id:
            try:
                garden_photo = GardenPhoto.objects.get(id=photo_id, user=request.user)
                # সরাসরি পাথ পাঠিয়ে কোয়ালিটি চেক
                quality_report = analyze_image_quality(garden_photo.image.path)
                if not quality_report.get('is_good_quality'):
                    return Response({
                        "status": "quality_warning",
                        "error": "Photo quality is poor.",
                        "issues": quality_report.get('issues'),
                        "photo_id": photo_id
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # কোয়ালিটি ভালো হলে প্রজেক্ট সেভ করার সময় এই ছবি ব্যবহার করুন
                serializer.save(user=request.user, photo=garden_photo.image)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            except GardenPhoto.DoesNotExist:
                return Response({"error": "Photo ID not found"}, status=status.HTTP_404_NOT_FOUND)

        # ২. যদি ইউজার সরাসরি নতুন ফাইল আপলোড করে
        elif image_file:
            # অস্থায়ীভাবে সেভ করছি পাথ পাওয়ার জন্য
            temp_photo = GardenPhoto.objects.create(user=request.user, image=image_file)
            try:
                quality_report = analyze_image_quality(temp_photo.image.path)
                if not quality_report.get('is_good_quality'):
                    return Response({
                        "status": "quality_warning",
                        "message": "Quality issues detected.",
                        "issues": quality_report.get('issues'),
                        "photo_id": temp_photo.id
                    }, status=status.HTTP_400_BAD_REQUEST)
                
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
            return Response({
                "photo_id": photo.id,
                "is_good_quality": report.get("is_good_quality"),
                "issues": report.get("issues")
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Standalone AI quality check failed: {str(e)}")
            return Response({"photo_id": photo.id, "error": "AI check failed"}, status=status.HTTP_201_CREATED)
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

@api_view(["GET", "DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def garden_project_detail(request, pk):
    project = get_object_or_404(GardenProject, pk=pk, user=request.user)
    if request.method == "GET":
        serializer = GardenProjectSerializer(project)
        return Response(serializer.data)
    elif request.method == "DELETE":
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)




@swagger_auto_schema(method="post", tags=["3. Garden Project"])
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def compose_garden(request):
    pass    
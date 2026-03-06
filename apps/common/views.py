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

from apps.common.ai.suggestions import GardenAIService
from apps.common.models import (
    GardenPhoto,
    GardenPreference,
    GardenProject,
    PrivacyPolicy,
    TermsConditions,
)
from apps.common.serializers import (
    GardenPhotoSerializer,
    GardenPreferenceSerializer,
    GardenProjectSerializer,
    PrivacyPolicySerializer,
    TermsConditionsSerializer,
)
from apps.common.services import PhotoQualityChecker
from apps.plants.models import Plant
from apps.plants.serializers import PlantSerializer


@swagger_auto_schema(method="get", tags=["common"])
@api_view(["GET"])
def get_privacy_policy(request):
    policy = PrivacyPolicy.objects.first()
    serializer = PrivacyPolicySerializer(policy)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="patch", request_body=PrivacyPolicySerializer, tags=["Cores"]
)
@api_view(["PATCH"])
def create_or_update_privacy_policy(request):
    policy = PrivacyPolicy.objects.first()
    serializer = PrivacyPolicySerializer(policy, data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method="get", tags=["Cores"])
@api_view(["GET"])
def get_terms_conditions(request):
    terms = TermsConditions.objects.first()
    serializer = TermsConditionsSerializer(terms)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="patch", request_body=TermsConditionsSerializer, tags=["Cores"]
)
@api_view(["PATCH"])
def create_or_update_terms_conditions(request):
    terms = TermsConditions.objects.first()

    serializer = TermsConditionsSerializer(terms, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(
        {"error": "Invalid data. Please check your input."},
        status=status.HTTP_400_BAD_REQUEST,
    )


# ============== Garden Project APIs ==============


@swagger_auto_schema(method="post", tags=["1. Garden Projects"])
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_garden_project(request):
    """
    Create a new garden project.
    Step 1: Name Your Project
    """
    serializer = GardenProjectSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method="get", tags=["1. Garden Projects"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_garden_project(request, project_id):
    """
    Retrieve a garden project by ID.
    """
    try:
        project = GardenProject.objects.get(id=project_id, user=request.user)
        serializer = GardenProjectSerializer(project)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except GardenProject.DoesNotExist:
        return Response(
            {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
        )


@swagger_auto_schema(method="get", tags=["1. Garden Projects"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def list_garden_projects(request):
    """
    List all garden projects for the authenticated user.
    """
    projects = GardenProject.objects.filter(user=request.user)
    serializer = GardenProjectSerializer(projects, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method="post", tags=["2. Garden Photos"])
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def upload_garden_photo(request, project_id):
    """
    Upload and analyze a garden photo.
    Step 2: Take a photo
    Step 3: Review Photo & detect quality

    Returns quality analysis with is_acceptable flag to determine next flow.
    """
    try:
        project = GardenProject.objects.get(id=project_id, user=request.user)
    except GardenProject.DoesNotExist:
        return Response(
            {
                "status": "error",
                "message": "Project not found",
                "data": None,
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # Delete previous photo if exists
    if hasattr(project, "garden_photo"):
        project.garden_photo.delete()

    serializer = GardenPhotoSerializer(data=request.data)
    if serializer.is_valid():
        photo = serializer.save(project=project)

        # Get the image file for quality analysis
        image_file = request.FILES.get("image")
        if not image_file:
            return Response(
                {
                    "status": "error",
                    "message": "No image file provided",
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check photo quality using OpenCV
        quality_result = PhotoQualityChecker.check_photo_quality(image_file)

        # Update photo with quality analysis results
        photo.quality_score = quality_result["quality_score"]
        photo.quality_issues = quality_result["issues"]
        photo.quality_status = "good" if quality_result["is_acceptable"] else "poor"
        photo.save()

        # Return response in required format
        status_code = (
            status.HTTP_200_OK
            if quality_result["is_acceptable"]
            else status.HTTP_202_ACCEPTED
        )

        return Response(
            {
                "status": "error" if not quality_result["is_acceptable"] else "success",
                "message": (
                    "Photo quality issues detected."
                    if not quality_result["is_acceptable"]
                    else "Photo uploaded successfully."
                ),
                "data": {
                    "photo_id": photo.id,
                    "image_url": photo.image.url if photo.image else None,
                    "quality_score": photo.quality_score,
                    "is_acceptable": quality_result["is_acceptable"],
                    "issues": photo.quality_issues,
                    "suggestion": "Pro Tip: Review our photo guide for best practices.",
                },
            },
            status=status_code,
        )
    print(f"Serializer Errors: {serializer.errors}")
    return Response(
        {
            "status": "error",
            "message": "Invalid image data",
            "data": None,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@swagger_auto_schema(method="get", tags=["2. Garden Photos"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_garden_photo(request, project_id):
    """
    Retrieve garden photo for a project.
    """
    try:
        project = GardenProject.objects.get(id=project_id, user=request.user)
        photo = project.garden_photo
        serializer = GardenPhotoSerializer(photo)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except GardenProject.DoesNotExist:
        return Response(
            {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except GardenPhoto.DoesNotExist:
        return Response(
            {"error": "No photo found for this project"},
            status=status.HTTP_404_NOT_FOUND,
        )


@swagger_auto_schema(method="delete", tags=["2. Garden Photos"])
@api_view(["DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def delete_garden_photo(request, project_id):
    """
    Delete garden photo for retake.
    Triggered when user clicks "Retake" button.
    """
    try:
        project = GardenProject.objects.get(id=project_id, user=request.user)
        photo = project.garden_photo
        photo.delete()
        return Response(
            {
                "status": "success",
                "message": "Photo deleted. Please retake a new photo.",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )
    except GardenProject.DoesNotExist:
        return Response(
            {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except GardenPhoto.DoesNotExist:
        return Response(
            {"error": "No photo found for this project"},
            status=status.HTTP_404_NOT_FOUND,
        )


@swagger_auto_schema(method="post", tags=["2. Garden Photos"])
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def confirm_photo_anyway(request, project_id):
    """
    Confirm to use the photo anyway despite quality issues.
    Triggered when user clicks "Use Anyway" button.
    Marks the photo as acceptable and proceeds to AI processing.
    """
    try:
        project = GardenProject.objects.get(id=project_id, user=request.user)
        photo = project.garden_photo

        # Force mark as acceptable/good
        photo.quality_status = "good"
        photo.save()

        return Response(
            {
                "status": "success",
                "message": "Photo accepted. Proceeding to analysis...",
                "data": {
                    "photo_id": photo.id,
                    "image_url": photo.image.url if photo.image else None,
                    "quality_score": photo.quality_score,
                    "is_acceptable": True,
                },
            },
            status=status.HTTP_200_OK,
        )
    except GardenProject.DoesNotExist:
        return Response(
            {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except GardenPhoto.DoesNotExist:
        return Response(
            {"error": "No photo found for this project"},
            status=status.HTTP_404_NOT_FOUND,
        )


# ============== Garden Preference APIs ==============


@swagger_auto_schema(method="post", tags=["3. Garden Preferences"])
@api_view(["POST", "PUT"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def save_garden_preference(request, project_id):
    """
    Save or update garden preferences (Steps 4-8).
    Supports partial updates (PUT) or full creation (POST).
    """
    try:
        project = GardenProject.objects.get(id=project_id, user=request.user)
    except GardenProject.DoesNotExist:
        return Response(
            {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
        )

    try:
        preference = project.garden_preference
        serializer = GardenPreferenceSerializer(
            preference, data=request.data, partial=True
        )
    except GardenPreference.DoesNotExist:
        serializer = GardenPreferenceSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(project=project)
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method="get", tags=["3. Garden Preferences"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_garden_preference(request, project_id):
    """
    Retrieve garden preferences for a project.
    """
    try:
        project = GardenProject.objects.get(id=project_id, user=request.user)
        preference = project.garden_preference
        serializer = GardenPreferenceSerializer(preference)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except GardenProject.DoesNotExist:
        return Response(
            {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except GardenPreference.DoesNotExist:
        return Response(
            {"error": "No preferences found for this project"},
            status=status.HTTP_404_NOT_FOUND,
        )


# ============== AI Plant Suggestions APIs ==============


@swagger_auto_schema(method="get", tags=["7. Garden Analysis"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_ai_plant_suggestions(request, project_id):
    """
    7.2 Get AI suggested plant names based on garden preferences.
    Uses OpenAI to analyze preferences and suggest suitable plants.
    """
    try:
        project = GardenProject.objects.get(id=project_id, user=request.user)
        preference = project.garden_preference
    except GardenProject.DoesNotExist:
        return Response(
            {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except GardenPreference.DoesNotExist:
        return Response(
            {
                "error": "No preferences found for this project. Please save preferences first."
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        # Get AI plant suggestions using the service
        plant_names = GardenAIService.get_plant_suggestions(preference)

        # Get display values
        display_values = GardenAIService.get_preference_display(preference)

        return Response(
            {
                "message": "AI analyzed your garden preferences. Here are suggested plants.",
                "garden_type": display_values["garden_type"],
                "sunlight": display_values["sunlight"],
                "soil_type": display_values["soil_type"],
                "suggested_plants": plant_names,
                "next_step": "Select a plant from the suggestions to view detailed care guide",
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": f"Failed to get AI suggestions: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@swagger_auto_schema(method="post", tags=["7. Garden Analysis"])
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_plant_details(request, project_id):
    """
    7.3 Get detailed plant information based on selected plant name.
    User selects a plant from AI suggestions and gets full care details.

    Request body: {"plant_name": "Tomato"}
    """
    try:
        project = GardenProject.objects.get(id=project_id, user=request.user)
    except GardenProject.DoesNotExist:
        return Response(
            {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
        )

    plant_name = request.data.get("plant_name")
    if not plant_name:
        return Response(
            {"error": "plant_name is required in request body"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Search for plant in database (case-insensitive)
        plant = Plant.objects.filter(common_name__iexact=plant_name).first()

        if not plant:
            return Response(
                {
                    "error": f"Plant '{plant_name}' not found in database",
                    "suggestion": "Double-check the plant name or try another suggestion",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PlantSerializer(plant, context={"request": request})

        return Response(
            {
                "message": f"Here are the detailed care instructions for {plant.common_name}",
                "plant_details": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": f"Failed to retrieve plant details: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============== Garden Analysis APIs ==============


@swagger_auto_schema(method="post", tags=["7. Garden Analysis"])
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_ai_recommendation_summary(request, project_id):
    """
    7.1.2 Get quick summary for a plant recommendation.
    User clicks a plant name to see key details before viewing full details.

    Request body: {"plant_name": "Tomato"}
    """
    try:
        project = GardenProject.objects.get(id=project_id, user=request.user)
        preference = project.garden_preference
    except GardenProject.DoesNotExist:
        return Response(
            {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except GardenPreference.DoesNotExist:
        return Response(
            {
                "error": "No preferences found for this project. Please save preferences first."
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    plant_name = request.data.get("plant_name")
    if not plant_name:
        return Response(
            {"error": "plant_name is required in request body"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get AI-generated summary for the selected plant
        plant_summary = GardenAIService.get_ai_plant_summary(preference, plant_name)

        return Response(
            {
                "message": f"Quick preview for {plant_name}",
                "plant_summary": plant_summary,
                "next_step": "Click 'View Details' to see complete care instructions and all information",
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": f"Failed to retrieve plant summary: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@swagger_auto_schema(method="post", tags=["7. Garden Analysis"])
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_ai_recommendation_details(request, project_id):
    """
    7.1.3 Get full details for a specific AI-generated plant recommendation.
    User views complete information after clicking 'View Details' from summary.

    Request body: {"plant_name": "Tomato"}
    """
    try:
        project = GardenProject.objects.get(id=project_id, user=request.user)
        preference = project.garden_preference
    except GardenProject.DoesNotExist:
        return Response(
            {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except GardenPreference.DoesNotExist:
        return Response(
            {
                "error": "No preferences found for this project. Please save preferences first."
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    plant_name = request.data.get("plant_name")
    if not plant_name:
        return Response(
            {"error": "plant_name is required in request body"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get AI-generated details for the selected plant
        plant_details = GardenAIService.get_ai_plant_detail(preference, plant_name)

        return Response(
            {
                "message": f"Here are the detailed care instructions for {plant_name}",
                "plant_details": plant_details,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": f"Failed to retrieve plant details: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@swagger_auto_schema(method="get", tags=["7. Garden Analysis"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_garden_recommendations(request, project_id):
    """
    7.1 Get AI analyzed garden recommendations based on preferences.
    Uses OpenAI to generate detailed plant recommendations that match
    the user's garden conditions, without querying the database.
    Returns AI-generated plant data following the database format.
    """
    try:
        project = GardenProject.objects.get(id=project_id, user=request.user)
        preference = project.garden_preference
    except GardenProject.DoesNotExist:
        return Response(
            {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except GardenPreference.DoesNotExist:
        return Response(
            {
                "error": "No preferences found for this project. Please save preferences first."
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        # Get AI-generated detailed plant recommendations
        recommended_plants = GardenAIService.get_detailed_plant_recommendations(
            preference
        )

        # Get display values for the response
        display_values = GardenAIService.get_preference_display(preference)

        total_area = preference.total_area_sq_ft or 0

        if not recommended_plants:
            return Response(
                {
                    "message": "Could not generate recommendations at this time. Try adjusting your garden preferences.",
                    "recommended_plants": [],
                },
                status=status.HTTP_200_OK,
            )

        # Extract plant names and images for initial response
        plant_recommendations = [
            {
                "plant_name": plant["common_name"],
                "plant_image": plant.get("main_image_url"),
            }
            for plant in recommended_plants
        ]

        return Response(
            {
                "message": "AI analyzed your garden. Here are the recommended plants. Click on any plant to see full details.",
                "garden_details": {
                    "project_name": project.name,
                    "sunlight": display_values["sunlight"],
                    "garden_type": display_values["garden_type"],
                    "soil_type": display_values["soil_type"],
                    "total_area_sq_ft": total_area,
                    "location": preference.location or "Not specified",
                },
                "recommended_plants": plant_recommendations,
                "next_step": "Select a plant to view summary and detailed care instructions",
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": f"Failed to generate AI recommendations: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

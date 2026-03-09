from django.urls import path

from apps.common.views import (
    confirm_photo_anyway,
    create_garden_project,
    create_or_update_privacy_policy,
    create_or_update_terms_conditions,
    delete_garden_photo,
    get_ai_plant_suggestions,
    get_ai_recommendation_info,
    get_garden_photo,
    get_garden_preference,
    get_garden_project,
    get_garden_recommendations,
    get_plant_details,
    get_privacy_policy,
    get_terms_conditions,
    list_garden_projects,
    save_garden_preference,
    upload_garden_photo,
)

urlpatterns = [
    path("privacy-policy/", get_privacy_policy, name="get-privacy-policy"),
    path(
        "privacy-policy/update/",
        create_or_update_privacy_policy,
        name="update-privacy-policy",
    ),
    # Terms & Conditions endpoints
    path("terms-conditions/", get_terms_conditions, name="get-terms-conditions"),
    path(
        "terms-conditions/update/",
        create_or_update_terms_conditions,
        name="update-terms-conditions",
    ),
    # 1. Garden Project APIs
    # 1.1 List Garden Projects
    path("gardens/projects/", list_garden_projects, name="list-garden-projects"),
    # 1.2 Create Garden Project
    path(
        "gardens/projects/create/", create_garden_project, name="create-garden-project"
    ),
    # 1.3 Get Garden Project
    path(
        "gardens/projects/<int:project_id>/",
        get_garden_project,
        name="get-garden-project",
    ),
    # 2. Garden Photo APIs
    # 2.1 Upload Garden Photo
    path(
        "gardens/projects/<int:project_id>/photo/",
        upload_garden_photo,
        name="upload-garden-photo",
    ),
    # 2.2 Get Garden Photo
    path(
        "gardens/projects/<int:project_id>/photo/view/",
        get_garden_photo,
        name="get-garden-photo",
    ),
    # 2.3 Delete Garden Photo
    path(
        "gardens/projects/<int:project_id>/photo/delete/",
        delete_garden_photo,
        name="delete-garden-photo",
    ),
    # 2.4 Confirm Photo Anyway
    path(
        "gardens/projects/<int:project_id>/photo/confirm-anyway/",
        confirm_photo_anyway,
        name="confirm-photo-anyway",
    ),
    # 3. Garden Preference APIs
    # 3.1 Save Garden Preference
    path(
        "gardens/projects/<int:project_id>/preference/",
        save_garden_preference,
        name="save-garden-preference",
    ),
    # 3.2 Get Garden Preference
    path(
        "gardens/projects/<int:project_id>/preference/view/",
        get_garden_preference,
        name="get-garden-preference",
    ),
    # 7.1 Get Garden AI based Recommendations
    path(
        "gardens/projects/<int:project_id>/recommendations/",
        get_garden_recommendations,
        name="get-garden-recommendations",
    ),
    # 7.1.2 Get AI Recommendation Info (Summary & Details)
    path(
        "gardens/projects/<int:project_id>/recommendations/info/",
        get_ai_recommendation_info,
        name="get-ai-recommendation-info",
    ),
    # 7.2 Get AI Plant Suggestions
    path(
        "gardens/projects/<int:project_id>/ai-plant-suggestions/",
        get_ai_plant_suggestions,
        name="get-ai-plant-suggestions",
    ),
    # 7.3 Get Plant Details
    path(
        "gardens/projects/<int:project_id>/plant-details/",
        get_plant_details,
        name="get-plant-details",
    ),
]

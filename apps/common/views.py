from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
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

from apps.accounts.models import User
from apps.common.models import (
    PrivacyPolicy,
    TermsConditions,
)
from apps.common.serializers import (
    DashboardPostSerializer,
    PrivacyPolicySerializer,
    TermsConditionsSerializer,
)
from apps.gardens.models import GardenProject
from apps.plants.models import Plant
from apps.posts.models import Post

# ─────────────────────────────────────────────────────────────
# Admin Dashboard
# ─────────────────────────────────────────────────────────────


@swagger_auto_schema(method="get", tags=["0. Admin Dashboard"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminUser])
def dashboard_stats(request):
    """0.1 Dashboard overview stats — Total Users, Active Today, Gardens Created, Total Plants"""
    today = timezone.now().date()
    return Response(
        {
            "total_users": User.objects.count(),
            "active_today": User.objects.filter(last_login__date=today).count(),
            "gardens_created": GardenProject.objects.count(),
            "total_plants": Plant.objects.count(),
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["0. Admin Dashboard"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminUser])
def dashboard_posts(request):
    """0.2 Latest posts list with pagination and search by user name/description"""
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 10))
    search = request.GET.get("search", "").strip()
    start = (page - 1) * limit
    end = start + limit

    qs = Post.objects.select_related("user").order_by("-created_at")

    if search:
        qs = qs.filter(
            Q(user__full_name__icontains=search) | Q(description__icontains=search)
        )

    total = qs.count()
    posts = qs[start:end]

    serializer = DashboardPostSerializer(posts, many=True, context={"request": request})
    return Response(
        {
            "data": serializer.data,
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="patch", tags=["0. Admin Dashboard"])
@api_view(["PATCH"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminUser])
def update_post_status(request, post_id):
    """0.3 Flag or publish a post"""

    post = get_object_or_404(Post, id=post_id)
    new_status = request.data.get("status")
    if new_status not in ("published", "flagged"):
        return Response(
            {"error": "status must be 'published' or 'flagged'"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    post.status = new_status
    post.save(update_fields=["status"])
    return Response({"id": post.id, "status": post.status}, status=status.HTTP_200_OK)


@swagger_auto_schema(method="delete", tags=["0. Admin Dashboard"])
@api_view(["DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminUser])
def delete_dashboard_post(request, post_id):
    """0.4 Delete a post from admin dashboard"""
    post = get_object_or_404(Post, id=post_id)
    post.delete()
    return Response(
        {"message": "Post deleted successfully"},
        status=status.HTTP_200_OK,
    )


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

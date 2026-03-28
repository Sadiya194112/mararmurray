from datetime import timedelta

from django.contrib.auth import authenticate
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timezone import now
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetSerializer,
    SendOTPSerializer,
    SignupSerializer,
    UserImageSerializer,
    UserSerializer,
    UserUpdateSerializer,
    VerifyOTPSerializer,
)
from apps.accounts.utils import get_tokens_for_user, send_email


@swagger_auto_schema(method="post", request_body=SignupSerializer, tags=["Accounts"])
@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    tokens = get_tokens_for_user(user)

    return Response(
        {
            "message": "Signup successful!",
            **tokens,
            "data": UserSerializer(user, context={"request": request}).data,
        },
        status=status.HTTP_201_CREATED,
    )


@swagger_auto_schema(method="post", request_body=SendOTPSerializer, tags=["Accounts"])
@api_view(["POST"])
def send_otp(request):
    serializer = SendOTPSerializer(data=request.data)
    if serializer.is_valid():
        try:
            user = User.objects.get(email=serializer.validated_data["email"])
        except User.DoesNotExist:
            return Response(
                {"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            otp = send_email(user.email)
        except Exception as e:
            return Response(
                {"message": "Failed to send OTP", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        user.otp = otp
        user.otp_expiry = timezone.now() + timedelta(minutes=2)
        user.save()
        return Response(
            {"message": "OTP sent successfully."}, status=status.HTTP_200_OK
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method="post", request_body=VerifyOTPSerializer, tags=["Accounts"])
@api_view(["POST"])
def verify_otp(request):
    serializer = VerifyOTPSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data.get("email").lower()
        otp = serializer.validated_data.get("otp")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "User does not exist."}, status=status.HTTP_400_BAD_REQUEST
            )

        if user.otp != otp:
            return Response(
                {"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_otp_expired():
            return Response(
                {"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST
            )

        # OTP is valid, reset it
        user.otp = None
        user.otp_expiry = None
        user.save()

        return Response(
            {
                "message": "OTP verified successfully.",
                "data": UserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method="post", request_body=LoginSerializer, tags=["Accounts"])
@api_view(["POST"])
def signin(request):
    serializer = LoginSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = get_tokens_for_user(user)

        user.last_login = now()
        user.save(update_fields=["last_login"])

        return Response(
            {
                "message": "Login successful!",
                **tokens,
                "data": UserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method="get", tags=["Accounts"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def get_profile(request):
    user = request.user
    serializer = UserSerializer(user, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="patch", request_body=UserUpdateSerializer, tags=["Accounts"]
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def user_update(request):
    serializer = UserUpdateSerializer(
        request.user, data=request.data, partial=True, context={"request": request}
    )
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "Profile updated successfully.", "data": serializer.data},
            status=status.HTTP_200_OK,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method="post", request_body=ChangePasswordSerializer, tags=["Accounts"]
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def change_password(request):
    user = request.user
    serializer = ChangePasswordSerializer(
        data=request.data, context={"request": request}
    )

    if serializer.is_valid():
        user.set_password(serializer.validated_data["password"])
        user.save()
        return Response(
            {"message": "Password changed successfully."}, status=status.HTTP_200_OK
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method="post", request_body=PasswordResetSerializer, tags=["Accounts"]
)
@api_view(["POST"])
def password_reset(request):
    serializer = PasswordResetSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"success": True, "message": "Password reset successfully."},
            status=status.HTTP_200_OK,
        )
    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )


@swagger_auto_schema(method="get", tags=["Accounts"])
@api_view(["GET"])
@permission_classes([IsAdminUser])
@authentication_classes([JWTAuthentication])
def users(request):
    """Admin users list with pagination and search by name/email."""
    search = request.GET.get("search", "").strip()
    page = request.GET.get("page", "1")
    limit = request.GET.get("limit", "10")

    try:
        page = int(page)
        limit = int(limit)
    except ValueError:
        return Response(
            {"error": "page and limit must be integers"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if page < 1 or limit < 1:
        return Response(
            {"error": "page and limit must be greater than 0"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    queryset = User.objects.annotate(
        projects_count=Count("garden_projects", distinct=True),
        posts_count=Count("posts", distinct=True),
    ).order_by("-date_joined")

    if search:
        queryset = queryset.filter(
            Q(full_name__icontains=search)
            | Q(username__icontains=search)
            | Q(email__icontains=search)
        )

    total = queryset.count()
    start = (page - 1) * limit
    end = start + limit
    items = queryset[start:end]

    data = [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "image": request.build_absolute_uri(user.image.url) if user.image else None,
            "status": "active" if user.is_active else "inactive",
            "projects_count": user.projects_count,
            "posts_count": user.posts_count,
            "joined": user.date_joined,
        }
        for user in items
    ]

    return Response(
        {
            "data": data,
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["Accounts"])
@api_view(["GET"])
@permission_classes([IsAdminUser])
@authentication_classes([JWTAuthentication])
def user_detail(request, user_id):
    """Admin user detail with account + activity summary."""
    user = get_object_or_404(User, id=user_id)
    gardens_created = user.garden_projects.count()
    posts_count = user.posts.count()

    return Response(
        {
            "id": user.id,
            "full_name": user.full_name,
            "username": user.username,
            "email": user.email,
            "website": user.website,
            "location": user.location,
            "role": user.role,
            "image": request.build_absolute_uri(user.image.url) if user.image else None,
            "status": "active" if user.is_active else "inactive",
            "is_active": user.is_active,
            "joined": user.date_joined,
            "last_login": user.last_login,
            "activity": {
                "gardens_created": gardens_created,
                "posts": posts_count,
            },
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(
    method="patch", request_body=UserUpdateSerializer, tags=["Accounts"]
)
@api_view(["PATCH"])
@permission_classes([IsAdminUser])
@authentication_classes([JWTAuthentication])
def user_edit(request, user_id):
    """Admin edit user profile fields."""
    user = get_object_or_404(User, id=user_id)

    requested_is_active = request.data.get("is_active")
    if user.is_superuser and requested_is_active is not None:
        normalized = str(requested_is_active).strip().lower()
        if normalized in {"false", "0", "no"}:
            return Response(
                {"error": "Super admin account cannot be deactivated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    serializer = UserUpdateSerializer(
        user, data=request.data, partial=True, context={"request": request}
    )
    if serializer.is_valid():
        serializer.save()
        return Response(
            {
                "message": "User updated successfully.",
                "data": UserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method="patch", tags=["Accounts"])
@api_view(["PATCH"])
@permission_classes([IsAdminUser])
@authentication_classes([JWTAuthentication])
def user_deactivate(request, user_id):
    """Admin deactivate user account."""
    user = get_object_or_404(User, id=user_id)

    if user.is_superuser:
        return Response(
            {"error": "Super admin account cannot be deactivated."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.is_active = False
    user.save(update_fields=["is_active"])
    return Response(
        {
            "message": "User deactivated successfully.",
            "id": user.id,
            "is_active": user.is_active,
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="patch", tags=["Accounts"])
@api_view(["PATCH"])
@permission_classes([IsAdminUser])
@authentication_classes([JWTAuthentication])
def user_activate(request, user_id):
    """Admin activate user account back to True."""
    # ১. ইউজারটিকে খুঁজে বের করুন (সে ডিঅ্যাক্টিভ থাকলেও এটি কাজ করবে)
    user = get_object_or_404(User, id=user_id)

    if user.is_active:
        return Response(
            {"message": "User is already active."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ২. ইউজারকে অ্যাক্টিভ করুন
    user.is_active = True
    user.save(update_fields=["is_active"])

    return Response(
        {
            "message": "User activated successfully.",
            "id": user.id,
            "is_active": user.is_active,
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="delete", tags=["Accounts"])
@api_view(["DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminUser])
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    return Response(
        {"message": "User deleted successfully."}, status=status.HTTP_200_OK
    )


@swagger_auto_schema(
    method="post",
    operation_description="Logout user by blacklisting the refresh token.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def logout(request):
    try:
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"error": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response(
            {"message": "Logged out successfully!"}, status=status.HTTP_200_OK
        )

    except Exception:
        return Response(
            {"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST
        )


@swagger_auto_schema(
    method="delete", operation_description="Delete the authenticated user's account."
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def delete_account(request):
    user = request.user
    user.delete()
    return Response(
        {"message": "Your account has been deleted successfully."},
        status=status.HTTP_200_OK,
    )


# ============== User Image APIs ==============


@swagger_auto_schema(method="post", tags=["6. User Images"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def upload_user_image(request):
    """6.1 Upload user profile image"""
    user = request.user
    image_file = request.FILES.get("image")
    if not image_file:
        return Response(
            {"message": "No image file provided"}, status=status.HTTP_400_BAD_REQUEST
        )
    user.image = image_file
    user.save()
    return Response(
        {"message": "Profile image uploaded successfully", "image_url": user.image.url},
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["6. User Images"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def get_user_image(request):
    """6.2 Get user profile image"""
    user = request.user
    if user.image:
        serializer = UserImageSerializer(user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response({"message": "No profile image"}, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(method="delete", tags=["6. User Images"])
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def delete_user_image(request):
    """6.3 Delete user profile image"""
    user = request.user
    if user.image:
        user.image.delete()
        user.image = None
        user.save()
        return Response(
            {"message": "Profile image deleted successfully"}, status=status.HTTP_200_OK
        )
    return Response(
        {"message": "No profile image to delete"}, status=status.HTTP_404_NOT_FOUND
    )

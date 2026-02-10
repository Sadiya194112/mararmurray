from datetime import timedelta

from django.contrib.auth import authenticate
from django.db.models import Q
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
    search = request.GET.get("search", "")
    # plan = request.GET.get("plan", "").lower()

    users = User.objects.all()

    # if plan in ["free", "pro"]:
    #     subscriptions = Subscription.objects.filter(is_active=True, plan__name__iexact=plan)
    #     user_ids = subscriptions.values_list("user_id", flat=True).distinct()
    #     users = users.filter(id__in=user_ids)

    # Apply search filter
    if search:
        users = users.filter(
            Q(name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
        )

    serializer = UserSerializer(users, many=True, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method="get", tags=["Accounts"])
@api_view(["GET"])
@permission_classes([IsAdminUser])
@authentication_classes([JWTAuthentication])
def user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    serializer = UserSerializer(user, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


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

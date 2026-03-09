from rest_framework import serializers

from apps.accounts.models import User


# -----------------------------
# Signup
# -----------------------------
class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    terms_and_conditions = serializers.BooleanField(required=True)

    class Meta:
        model = User
        fields = ["full_name", "email", "password", "terms_and_conditions"]

    def validate_terms_and_conditions(self, value):
        if value is not True:
            raise serializers.ValidationError(
                {"error": "You must agree to the terms and conditions."}
            )
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


# -----------------------------
# OTP
# -----------------------------
class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()


# -----------------------------
# Login
# -----------------------------
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        # ১. ইউজারকে তার ইমেইল দিয়ে খুঁজে বের করা
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"error": "Invalid email or password."})

        # ২. পাসওয়ার্ড চেক করা
        if not user.check_password(password):
            raise serializers.ValidationError({"error": "Invalid email or password."})

        # ৪. ইউজার একটিভ আছে কি না চেক করা
        if not user.is_active:
            raise serializers.ValidationError("This account is disabled.")

        # ভ্যালিডেশনে পাস করলে ইউজার অবজেক্টটি ডাটাতে যোগ করে দিন
        data["user"] = user
        return data


# -----------------------------
# User Serializer
# -----------------------------
class UserSerializer(serializers.ModelSerializer):
    # role = serializers.CharField(source="get_role_display", read_only=True)
    # student_name = serializers.CharField(
    #     source="student_profile.full_name", read_only=True
    # )

    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "email",
            "is_active",
            "date_joined",
            "last_login",
        )
        read_only_fields = ["email", "is_active", "date_joined", "last_login"]


# -----------------------------
# Password Serializers
# -----------------------------
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect current password.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        email = data["email"].lower()
        data["email"] = email
        try:
            user = User.objects.get(email=data["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})

        # if not user.is_verified:
        #     raise serializers.ValidationError({"otp": "OTP verification required."})

        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        return data

    def save(self, **kwargs):
        user = User.objects.get(email=self.validated_data["email"])
        user.set_password(self.validated_data["password"])
        user.otp = None
        user.otp_expiry = None
        # user.is_verified = False
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["full_name", "username", "website", "location", "image"]

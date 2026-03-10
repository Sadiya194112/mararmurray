from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, full_name, email, password=None, **extra_fields):
        if not full_name:
            raise ValueError("Full Name must be set.")
        if not email:
            raise ValueError("Email must be set.")

        email = self.normalize_email(email)

        # এখানে সরাসরি full_name পাস করতে হবে
        user = self.model(full_name=full_name, email=email, **extra_fields)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, full_name, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(full_name, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("student", "Student"),
        ("university", "University"),
    ]
    full_name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True, blank=True)
    website = models.URLField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)

    # Status fields
    is_approved = models.BooleanField(default=False)  # Specific to University
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    last_login = models.DateTimeField(null=True, blank=True)

    otp = models.CharField(max_length=6, null=True, blank=True, editable=False)
    otp_expiry = models.DateTimeField(null=True, blank=True, editable=False)

    terms_and_conditions = models.BooleanField(default=False)
    image = models.ImageField(upload_to="profile_pictures/", blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        return self.email

    def is_otp_expired(self):
        return self.otp_expiry and timezone.now() > self.otp_expiry

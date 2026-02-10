from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import ValidationError

from apps.accounts.models import User

# Register your models here.
# -------------------- User Admin --------------------

# -------------------- User Forms --------------------


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Password confirmation", widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ["full_name", "email", "role"]

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = [
            "full_name",
            "email",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        ]


class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = [
        "id",
        "full_name",
        "email",
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
    ]
    list_filter = ["role", "is_active", "is_staff", "is_superuser"]

    readonly_fields = ["last_login", "date_joined"]

    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("User Info", {"fields": ["name", "phone", "role"]}),
        (
            "Permissions",
            {
                "fields": [
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ]
            },
        ),
        ("Important dates", {"fields": ["last_login", "date_joined"]}),
    ]

    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["name", "email", "phone", "role", "password1", "password2"],
            },
        ),
    ]

    search_fields = ["email", "name", "phone"]
    ordering = ["email"]
    filter_horizontal = ["groups", "user_permissions"]

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


admin.site.register(User, UserAdmin)

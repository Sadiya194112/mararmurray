from django.urls import path

from apps.accounts.views import (
    change_password,
    delete_account,
    get_profile,
    logout,
    password_reset,
    send_otp,
    signin,
    signup,
    user_delete,
    user_detail,
    user_update,
    verify_otp,
)

urlpatterns = [
    path("signup/", signup, name="signup"),
    path("signin/", signin, name="signin"),
    path("send-otp/", send_otp, name="send_otp"),
    path("verify-otp/", verify_otp, name="verify_otp"),
    path("reset-password/", password_reset, name="password_reset"),
    path("change-password/", change_password, name="change_password"),
    path("profile/", get_profile, name="get-profile"),
    path(
        "user/detail/<int:user_id>/", user_detail, name="user_detail"
    ),  # Admin will get user detail by id
    path("user/edit/", user_update, name="user_update"),
    path("logout/", logout, name="logout"),
    path("delete-account/", delete_account, name="delete_account"),
    path(
        "users/<int:user_id>/delete/", user_delete, name="user_delete"
    ),  # Will be deleted by admin
]

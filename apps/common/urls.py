from django.urls import path

from apps.common.views import (
    contact_us,
    create_or_update_privacy_policy,
    create_or_update_terms_conditions,
    dashboard_posts,
    dashboard_stats,
    delete_dashboard_post,
    get_privacy_policy,
    get_terms_conditions,
    update_post_status,
)

urlpatterns = [
    # 0. Admin Dashboard
    path("dashboard/stats/", dashboard_stats, name="dashboard-stats"),
    path("dashboard/posts/", dashboard_posts, name="dashboard-posts"),
    path(
        "dashboard/posts/<int:post_id>/status/",
        update_post_status,
        name="update-post-status",
    ),
    path(
        "dashboard/posts/<int:post_id>/delete/",
        delete_dashboard_post,
        name="delete-dashboard-post",
    ),
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
    path("contact-us/", contact_us, name="contact-us"),
]

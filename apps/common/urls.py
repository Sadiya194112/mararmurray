from django.urls import path

from apps.common.views import (
    create_or_update_privacy_policy,
    create_or_update_terms_conditions,
    get_privacy_policy,
    get_terms_conditions,
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
]

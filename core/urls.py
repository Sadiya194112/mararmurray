from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/v1/",
        include(
            [
                path("accounts/", include("apps.accounts.urls")),
                path("", include("apps.common.urls")),
                path("plants/", include("apps.plants.urls")),
                # path("posts/", include("apps.posts.urls")),
            ]
        ),
    ),
]

# The url for static and media files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Florle API",
        default_version="v1",
        description="API documentation for Florle garden planning app",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@florle.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("admin/", admin.site.urls),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui-alt",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("swagger.json", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path(
        "api/v1/",
        include(
            [
                path("accounts/", include("apps.accounts.urls")),
                path("", include("apps.common.urls")),
                path("plants/", include("apps.plants.urls")),
                path("", include("apps.gardens.urls")),
                path("", include("apps.posts.urls")),
            ]
        ),
    ),
]

# The url for static and media files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

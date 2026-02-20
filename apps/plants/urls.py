from django.urls import path

from apps.plants.views import sync_plants_view

urlpatterns = [
    path("sync-plants-action/", sync_plants_view, name="sync-plants-url"),
]

from django.contrib import messages
from django.shortcuts import redirect

from apps.plants.services import PlantSyncService


def sync_plants_view(request):
    count = PlantSyncService.sync_all_plants(start_id=1, end_id=20)
    messages.success(request, f"সফলভাবে {count}টি গাছ ডাটাবেসে যোগ করা হয়েছে!")
    return redirect("plant-database-page")

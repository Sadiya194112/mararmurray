import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.gardens.models import Plant
from apps.plants.ai.perenual import PerenualHarvester

from .tasks import download_plant_image_task  # টাস্কটি ইম্পোর্ট করুন


class Command(BaseCommand):
    help = "Syncs high-quality data from Perenual API"

    def handle(self, *args, **options):
        api_key = settings.PERENUAL_API_KEY
        harvester = PerenualHarvester(api_key)

        # ১ নম্বর পেজ থেকে হার্ভেস্ট শুরু
        species_list = harvester.harvest_batch(page=1)

        for species in species_list:
            sci_name = species["scientific_name"][0]

            # ডুপ্লিকেট চেক
            if Plant.objects.filter(scientific_name__icontains=sci_name).exists():
                self.stdout.write(f"Skipping {species['common_name']} - exists.")
                continue

            full_data = harvester.get_details(species["id"])
            if not full_data:
                continue

            mapped_data = harvester.map_to_model(full_data)

            # ১. ডাটাবেসে সেভ (খুব দ্রুত হবে)
            plant = Plant.objects.create(**mapped_data)

            # ২. Celery Task কল করা (Background processing)
            # এটি ডাউনলোড না করে শুধু কিউ (Queue) তে পাঠিয়ে দেবে
            if mapped_data.get("main_image_url"):
                download_plant_image_task.delay(plant.id, mapped_data["main_image_url"])

            self.stdout.write(
                self.style.SUCCESS(
                    f"Data saved for: {plant.common_name}. Image download queued."
                )
            )

            time.sleep(1)

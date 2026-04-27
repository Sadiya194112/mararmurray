import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.plants.ai.perenual import PerenualHarvester
from apps.plants.ai.tasks import download_plant_image_task
from apps.plants.models import HarvestMetadata, Plant


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=5)

    def handle(self, *args, **options):
        target_count = options["count"]
        api_key = settings.PERENUAL_API_KEY
        harvester = PerenualHarvester(api_key)

        metadata, created = HarvestMetadata.objects.get_or_create(id=1)
        current_page = metadata.last_processed_page

        self.stdout.write(
            self.style.WARNING(f"🚀 Starting from Page {current_page}...")
        )

        processed_count = 0

        while processed_count < target_count:
            species_list = harvester.harvest_batch(page=current_page)

            if not species_list:
                self.stdout.write(self.style.ERROR("❌ No more data in API."))
                break

            new_plants_found_in_this_page = False
            plants_already_exists_count = 0

            for species in species_list:
                if processed_count >= target_count:
                    break

                sci_name = species.get("scientific_name", ["Unknown"])[0]

                # চেক করা গাছটি ডাটাবেসে আছে কি না
                if Plant.objects.filter(scientific_name__icontains=sci_name).exists():
                    plants_already_exists_count += 1
                    continue

                # নতুন গাছ পাওয়া গেছে
                new_plants_found_in_this_page = True
                full_data = harvester.get_details(species["id"])
                if not full_data:
                    continue

                mapped_data = harvester.map_to_model(full_data)
                plant = Plant.objects.create(**mapped_data)

                if mapped_data.get("main_image_url"):
                    download_plant_image_task.delay(
                        plant.id, mapped_data["main_image_url"]
                    )

                processed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"   [{processed_count}/{target_count}] Saved: {plant.common_name}"
                    )
                )
                time.sleep(0.5)

            # --- গুরুত্বপূর্ণ লজিক পরিবর্তন ---

            # যদি এই পেজের ৩০টি গাছের সবকটিই অলরেডি ডাটাবেসে থাকে,
            # শুধুমাত্র তখনই আমরা পরবর্তী পেজে যাব।
            if (
                plants_already_exists_count == len(species_list)
                and len(species_list) > 0
            ):
                current_page += 1
                metadata.last_processed_page = current_page
                metadata.save()
                self.stdout.write(
                    self.style.NOTICE(
                        f"🔄 All plants in Page {current_page - 1} exist. Moving to Page {current_page}"
                    )
                )
            else:
                # পেজে এখনও নতুন গাছ থাকতে পারে অথবা কোটা পূরণ হয়ে গেছে,
                # তাই পেজ নম্বর বাড়ানো হবে না।
                self.stdout.write(f"📍 Staying on Page {current_page} for next run.")
                break

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✨ Harvested {processed_count} plants. Metadata remains at Page {current_page}."
            )
        )

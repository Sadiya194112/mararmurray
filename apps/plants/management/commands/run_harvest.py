import time

from django.conf import settings
from django.core.management.base import BaseCommand
from apps.plants.ai.tasks import enrich_and_download_task

from apps.plants.ai.perenual import PerenualHarvester
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

            for species in species_list:
                if processed_count >= target_count:
                    break

                sci_name = species.get("scientific_name", ["Unknown"])[0]

                # চেক করা গাছটি ডাটাবেসে আছে কি না
                if Plant.objects.filter(scientific_name__icontains=sci_name).exists():
                    continue

                full_data = harvester.get_details(species["id"])
                if not full_data:
                    continue

                # Filter: The plant MUST be outdoor and MUST have flowers
                if full_data.get("indoor") is True or full_data.get("flowers") is False:
                    self.stdout.write(self.style.WARNING(f"   Skipping {sci_name} (Indoor or Non-flowering)"))
                    continue

                mapped_data = harvester.map_to_model(full_data)
            
                # ডাটাবেসে শুধুমাত্র এপিআই থেকে পাওয়া ডাটা দিয়ে এন্ট্রি করা
                plant = Plant.objects.create(**mapped_data)

                # --- ব্যাকগ্রাউন্ডে AI এবং ইমেজ ডাউনলোডের কাজ পাঠানো ---
                enrich_and_download_task.delay(plant.id, mapped_data)

                processed_count += 1
                self.stdout.write(self.style.SUCCESS(f"   [{processed_count}/{target_count}] Basic data saved: {plant.common_name}. AI enrichment queued."))
                time.sleep(0.5)

            # --- গুরুত্বপূর্ণ লজিক পরিবর্তন ---

            if processed_count >= target_count:
                # কোটা পূরণ হয়ে গেছে। পেজে এখনও নতুন গাছ থাকতে পারে,
                # তাই পেজ নম্বর বাড়ানো হবে না।
                self.stdout.write(f"📍 Staying on Page {current_page} for next run.")
                break
            else:
                # কোটা পূরণ হয়নি কিন্তু এই পেজের সব গাছ চেক করা শেষ,
                # তাই পরবর্তী পেজে যেতে হবে।
                current_page += 1
                metadata.last_processed_page = current_page
                metadata.save()
                self.stdout.write(
                    self.style.NOTICE(
                        f"🔄 Finished Page {current_page - 1}. Moving to Page {current_page}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✨ Harvested {processed_count} plants. Metadata remains at Page {current_page}."
            )
        )

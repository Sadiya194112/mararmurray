import time

from django.core.management.base import BaseCommand

from apps.plants.services import PlantSyncService


class Command(BaseCommand):
    help = "Command to sync all plant data from the Perenual API"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Data synchronization has started..."))

        # Assuming plant IDs exist up to 10104 based on the API documentation
        start_id = 1
        end_id = 2  # Total species: 10104

        success_count = 0
        for species_id in range(start_id, end_id + 1):
            try:
                # আপনার তৈরি করা সার্ভিস ক্লাস ব্যবহার করছি
                plant, created = PlantSyncService.sync_plant_by_id(species_id)

                if plant:
                    success_count += 1
                    status = "created" if created else "updated"
                    self.stdout.write(
                        f"ID {species_id}: {plant.common_name} - {status}"
                    )

                # API Rate Limit এড়াতে প্রতি ১০টি রিকোয়েস্ট পর ছোট বিরতি
                if species_id % 10 == 0:
                    time.sleep(1)

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error occurred for ID {species_id}: {e}")
                )
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully synchronized data for {success_count} plants!"
            )
        )

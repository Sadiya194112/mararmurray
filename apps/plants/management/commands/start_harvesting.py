import os

from django.core.management.base import BaseCommand

from ai_plant_engine.harvester.engine import HarvestEngine
from apps.plants.models import Plant


class Command(BaseCommand):
    help = "Starts the AI Plant Harvester in the background"

    @staticmethod
    def _normalize_plant_type(value):
        if not value:
            return None
        normalized = str(value).strip().lower()
        if normalized in {"annual", "perenial", "both"}:
            return normalized
        if normalized == "perennial":
            return "perenial"
        if "annual" in normalized and (
            "perennial" in normalized or "perenial" in normalized
        ):
            return "both"
        return None

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=7, help="Number of days to run the harvester"
        )
        parser.add_argument(
            "--rate", type=int, default=5, help="Plants per hour to harvest"
        )

    def handle(self, *args, **options):
        days = options["days"]
        rate = options["rate"]

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            self.stdout.write(
                self.style.ERROR("OPENAI_API_KEY environment variable is missing.")
            )
            return

        def get_existing_plants():
            return list(Plant.objects.values_list("common_name", flat=True))

        def insert_harvested_plants(harvested_data_list):
            self.stdout.write(
                f"Inserting {len(harvested_data_list)} harvested plants into DB..."
            )
            for data in harvested_data_list:
                plant_type = self._normalize_plant_type(data.get("plant_type"))
                # Fix URL fields if AI returns placeholder text instead of actual URL
                main_url = data.get("main_image_url", "")
                if "string" in main_url.lower() or "url" in main_url.lower():
                    main_url = ""

                shop_url = data.get("shopping_link", "")
                if "string" in shop_url.lower() or "url" in shop_url.lower():
                    shop_url = ""

                Plant.objects.update_or_create(
                    common_name=data.get("common_name", ""),
                    defaults={
                        "scientific_name": data.get("scientific_name", ""),
                        "plant_type": plant_type,
                        "color": data.get("color", ""),
                        "description": data.get("description", ""),
                        "main_image_url": main_url,
                        "sunlight": data.get("sunlight", ""),
                        "water": data.get("water", ""),
                        "spacing": data.get("spacing", ""),
                        "growth_size": data.get("growth_size", ""),
                        "season": data.get("season", ""),
                        "difficulty": data.get("difficulty", ""),
                        "care_guide": data.get("care_guide", ""),
                        "bloom_spring": data.get("bloom_spring", False),
                        "bloom_summer": data.get("bloom_summer", False),
                        "bloom_fall": data.get("bloom_fall", False),
                        "bloom_winter": data.get("bloom_winter", False),
                        "shopping_link": shop_url,
                        "tags": data.get("tags", ""),
                        "family": data.get("family", ""),
                        "propagation": data.get("propagation", ""),
                    },
                )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully inserted {len(harvested_data_list)} plants."
                )
            )

        try:
            self.stdout.write(
                f"Starting AI Plant Harvest Background Task ({days} days, {rate} plants/hr)..."
            )
            engine = HarvestEngine(openai_api_key=api_key)

            engine.start_background_harvesting(
                days=days,
                plants_per_hour=rate,
                insert_callback=insert_harvested_plants,
                get_existing_plants_callback=get_existing_plants,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Background task started successfully. Keep this terminal open to continue harvesting."
                )
            )
            self.stdout.write(self.style.WARNING("(Press Ctrl+C to stop)"))

            # Keep the main thread alive since the background thread is a daemon
            import time

            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nStopping harvester..."))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Could not start AI plant background harvester: {e}")
            )

import os

import requests

from apps.plants.models import Plant


class PlantSyncService:
    BASE_URL = "https://perenual.com/api/v2/species/details/"
    API_KEY = os.getenv("PERENUAL_API_KEY")

    @classmethod
    def sync_all_plants(cls, start_id=1, batch_size=100):
        """Sync plants in batches from Perenual API"""
        end_id = start_id + batch_size - 1
        success_count = 0

        print(f"Syncing from ID {start_id} to {end_id}...")

        for i in range(start_id, end_id + 1):
            plant, created = cls.sync_plant_by_id(i)
            if plant:
                success_count += 1

        return success_count, end_id

    @classmethod
    def sync_plant_by_id(cls, species_id):
        """
        Sync a single plant from Perenual API and save to database.
        Maps API response fields to Plant model fields correctly:
        - type -> plant_type
        - description -> description
        - sunlight (array) -> sunlight (joined)
        - watering -> water
        - care_guides -> care_guide
        - care_level -> difficulty
        - dimensions[0] -> growth_size (formatted as "min-max unit")
        - cycle -> season
        - propagation (array) -> propagation (joined)
        - scientific_name[0] -> scientific_name
        """
        url = f"{cls.BASE_URL}{species_id}?key={cls.API_KEY}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()

                # Extract scientific name (first element from array)
                sci_names = data.get("scientific_name") or []
                scientific_name = sci_names[0] if sci_names else f"Unknown-{species_id}"

                # Growth Size - Format: "min-max unit"
                dimensions = data.get("dimensions") or []
                growth_size = None
                if dimensions and isinstance(dimensions, list):
                    dim = dimensions[0]
                    min_val = dim.get("min_value")
                    max_val = dim.get("max_value")
                    unit = dim.get("unit", "")
                    if min_val is not None and max_val is not None:
                        growth_size = f"{min_val}-{max_val} {unit}".strip()

                # Image - Use regular_url or fallback to original_url
                image_data = data.get("default_image") or {}
                image_url = image_data.get("regular_url") or image_data.get(
                    "original_url"
                )

                # Sunlight (Array -> Comma-separated string)
                sunlight_list = data.get("sunlight") or []
                sunlight_str = (
                    ", ".join(sunlight_list) if isinstance(sunlight_list, list) else ""
                )

                # Propagation (Array -> Comma-separated string, deduplicated)
                propagation_list = data.get("propagation") or []
                propagation_str = (
                    ", ".join(set(propagation_list))
                    if isinstance(propagation_list, list)
                    else ""
                )

                # Care Guide - Use description field
                care_guide = data.get("description", "")

                # Water - From watering field
                water = data.get("watering")

                # Spacing - Default value since API doesn't provide it
                spacing = "Check manual guide"

                # Log extracted data
                print(f"\n=== Syncing Plant ID {species_id} ===")
                print(f"Common Name: {data.get('common_name')}")
                print(f"Scientific Name: {scientific_name}")
                print(f"Plant Type: {data.get('type')}")
                print(f"Sunlight: {sunlight_str}")
                print(f"Water: {water}")
                print(f"Growth Size: {growth_size}")
                print(f"Season (Cycle): {data.get('cycle')}")
                print(f"Difficulty (Care Level): {data.get('care_level')}")
                print(f"Image URL: {image_url}")
                print(f"Family: {data.get('family')}")
                print(f"Propagation: {propagation_str}\n")

                # Save to database using update_or_create
                plant, created = Plant.objects.update_or_create(
                    scientific_name=scientific_name,
                    defaults={
                        "common_name": data.get("common_name", "Unknown"),
                        "plant_type": data.get("type"),
                        "description": data.get("description"),
                        "main_image_url": image_url,
                        "sunlight": sunlight_str,
                        "water": water,
                        "growth_size": growth_size,
                        "season": data.get("cycle"),
                        "difficulty": data.get("care_level"),
                        "care_guide": care_guide,
                        "spacing": spacing,
                        "family": data.get("family"),
                        "propagation": propagation_str,
                        # bloom_* fields default to False (set by model)
                    },
                )
                status = "Created" if created else "Updated"
                print(f"✓ Successfully {status}: {scientific_name}\n")
                return plant, created
            else:
                print(f"Skipping ID {species_id}: Status {response.status_code}")
        except Exception as e:
            print(f"Error syncing ID {species_id}: {e}")
        return None, False

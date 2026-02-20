import os

import requests

from apps.plants.models import Plant


class PlantSyncService:
    BASE_URL = "https://perenual.com/api/species/details/"
    API_KEY = os.getenv("PERENUAL_API_KEY")
    print(f"Using Perenual API Key: {API_KEY}")

    @classmethod
    def sync_plant_by_id(cls, species_id):
        """১. একটি নির্দিষ্ট আইডি ধরে ডাটা সিঙ্ক করার ফাংশন"""
        url = f"{cls.BASE_URL}{species_id}?key={cls.API_KEY}"

        try:
            response = requests.get(url, timeout=10)
            print(f"Checking ID {species_id}: Status Code {response.status_code}")
            if response.status_code == 200:
                data = response.json()

                # scientific_name লিস্ট হিসেবে আসে, তাই প্রথমটি নিতে হবে
                sci_name_list = data.get("scientific_name", [])
                sci_name = (
                    sci_name_list[0] if sci_name_list else f"Unknown-{species_id}"
                )

                image_data = data.get("default_image") or {}
                image_url = image_data.get("regular_url") or image_data.get(
                    "original_url"
                )

                sunlight_raw = data.get("sunlight", [])
                sunlight_str = (
                    ", ".join(sunlight_raw)
                    if isinstance(sunlight_raw, list)
                    else str(sunlight_raw)
                )

                propagation_raw = data.get("propagation", [])
                propagation_str = (
                    ", ".join(propagation_raw)
                    if isinstance(propagation_raw, list)
                    else str(propagation_raw)
                )

                # ডাটা সেভ বা আপডেট
                plant, created = Plant.objects.update_or_create(
                    scientific_name=sci_name,
                    defaults={
                        "common_name": data.get("common_name", "Unknown"),
                        "plant_type": data.get("type"),
                        "description": data.get("description"),
                        "main_image_url": image_url,
                        "sunlight": sunlight_str,
                        "water": data.get("watering"),
                        "difficulty": data.get("care_level"),
                        "family": data.get("family"),
                        "propagation": propagation_str,
                    },
                )
                return plant, created
            else:
                print(f"API Error for ID {species_id}: Status Code {response.text}")
        except Exception as e:
            print(f"Error syncing ID {species_id}: {e}")

        return None, False

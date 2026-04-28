import json
import logging

import requests
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class PerenualHarvester:
    BASE_URL = "https://perenual.com/api/v2"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def harvest_batch(self, page: int = 1):
        url = f"{self.BASE_URL}/species-list?key={self.api_key}&page={page}"
        logger.info(f"📡 Fetching batch list from: {url}")
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()

                # --- এই অংশটি যোগ করুন ---
                print("\n" + "=" * 50)
                print(f"📦 FULL BATCH RESPONSE (Page {page}):")
                print(json.dumps(data, indent=4))  # পুরো JSON সুন্দরভাবে প্রিন্ট করবে
                print("=" * 50 + "\n")
                # -----------------------

                return data.get("data", [])
        except Exception as e:
            logger.error(f"💥 Batch fetch failed: {e}")
        return []

    def get_details(self, species_id: int):
        url = f"{self.BASE_URL}/species/details/{species_id}?key={self.api_key}"
        logger.info(f"📡 Fetching details for Species ID: {species_id}")
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()

                # --- এই অংশটি যোগ করুন ---
                print("\n" + "-" * 50)
                print(f"📄 FULL DETAIL RESPONSE (ID {species_id}):")
                print(json.dumps(data, indent=4))
                print("-" * 50 + "\n")
                # -----------------------

                return data
            else:
                logger.warning(
                    f"⚠️ Detail fetch failed with status: {response.status_code}"
                )
        except Exception as e:
            logger.error(f"💥 Detail fetch failed for ID {species_id}: {e}")
        return None

    def map_to_model(self, data: dict):
        """এপিআই ডাটাকে জ্যাঙ্গো মডেলের ফিল্ডে রূপান্তর করে।"""
        if not data:
            return {}

        sci_names = data.get("scientific_name", [])
        sci_name = sci_names[0] if sci_names else "Unknown"

        # Sunlight Mapping
        raw_sunlight = data.get("sunlight") or []
        sun_list = [s.lower() for s in raw_sunlight if s]

        sunlight = "full_sun"
        if "full shade" in sun_list:
            sunlight = "full_shade"
        elif "part shade" in sun_list:
            sunlight = "partial_sun"

        # Bloom Season Logic
        # API uses 'flowering_season' or sometimes 'bloom_time'
        bloom_months = str(data.get("flowering_season") or data.get("bloom_time") or "").lower()

        # Image URL extraction
        default_img = data.get("default_image") or {}
        img_url = default_img.get("original_url") or ""

        # Extra Data extraction
        spacing = ""
        spacing_data = data.get("xPlantSpacingRequirement")
        if isinstance(spacing_data, dict):
            val = spacing_data.get("value", "")
            unit = spacing_data.get("unit", "")
            if val and unit:
                spacing = f"{val} {unit}"

        growth_size = ""
        dim = data.get("dimensions", [])
        if dim and isinstance(dim, list) and len(dim) > 0:
            for d in dim:
                if d.get("type") == "Height":
                    min_v = d.get("min_value")
                    max_v = d.get("max_value")
                    unit = d.get("unit", "")
                    if min_v and min_v == max_v:
                        growth_size = f"{min_v} {unit} tall"
                    elif min_v and max_v:
                        growth_size = f"{min_v}-{max_v} {unit} tall"

        # Soil extraction
        soil_list = data.get("soil", [])
        soil_str = ", ".join([str(s) for s in soil_list]) if soil_list else ""

        return {
            "common_name": data.get("common_name", "Unknown"),
            "scientific_name": sci_name,
            "plant_type": self._map_plant_type(data.get("cycle")),
            "description": data.get("description", ""),
            "main_image_url": img_url,
            "sunlight": sunlight,
            "water": data.get("watering", "Average"),
            "soil_type": soil_str,  # Will be passed as hint_soil_type to AI
            "garden_type": "",      # Will force AI to figure it out instead of defaulting to flower_garden
            "difficulty": data.get("care_level", "Medium"),
            "family": data.get("family", ""),
            "spacing": spacing,
            "growth_size": growth_size,
            "care_guide": data.get("care_guide", "Follow standard botanical care."),
            "bloom_spring": any(m in bloom_months for m in ["march", "april", "may", "spring"]),
            "bloom_summer": any(m in bloom_months for m in ["june", "july", "august", "summer"]),
            "bloom_fall": any(
                m in bloom_months for m in ["september", "october", "november", "fall", "autumn"]
            ),
            "bloom_winter": any(
                m in bloom_months for m in ["december", "january", "february", "winter"]
            ),
            "propagation": ", ".join(data.get("propagation", []) or []),
            "tags": ", ".join(
                [
                    str(t)
                    for t in (data.get("attracts", []) or [])
                    + (data.get("propagation", []) or [])
                    if t
                ]
            ),
        }

    def _map_plant_type(self, cycle):
        if not cycle:
            return "perenial"
        cycle_str = str(cycle).lower()
        if "perennial" in cycle_str:
            return "perenial"
        if "annual" in cycle_str:
            return "annual"
        return "both"

    def download_and_save_image(self, plant_instance, url):
        """ইমেজ ডাউনলোড করে Media ফোল্ডারে সেভ করে।"""
        if not url or "profile/default" in url:
            return
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                fname = f"plant_{plant_instance.id}_{plant_instance.scientific_name.replace(' ', '_')}.jpg"
                plant_instance.image.save(fname, ContentFile(resp.content), save=True)
        except Exception as e:
            logger.error(f"Image download failed for {plant_instance.common_name}: {e}")

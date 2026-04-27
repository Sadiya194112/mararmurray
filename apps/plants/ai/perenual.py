import json
import logging

import requests
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class PerenualHarvester:
    BASE_URL = "https://perenual.com/api"

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
        bloom_months = str(data.get("bloom_time") or "").lower()

        # Image URL extraction
        default_img = data.get("default_image") or {}
        img_url = default_img.get("original_url") or ""

        return {
            "common_name": data.get("common_name", "Unknown"),
            "scientific_name": sci_name,
            "plant_type": self._map_plant_type(data.get("cycle")),
            "description": data.get("description", ""),
            "main_image_url": img_url,
            "sunlight": sunlight,
            "water": data.get("watering", "Average"),
            "difficulty": data.get("care_level", "Medium"),
            "family": data.get("family", ""),
            "care_guide": data.get("care_guide", "Follow standard botanical care."),
            "bloom_spring": any(m in bloom_months for m in ["march", "april", "may"]),
            "bloom_summer": any(m in bloom_months for m in ["june", "july", "august"]),
            "bloom_fall": any(
                m in bloom_months for m in ["september", "october", "november"]
            ),
            "bloom_winter": any(
                m in bloom_months for m in ["december", "january", "february"]
            ),
            "tags": ", ".join(
                [
                    str(t)
                    for t in (data.get("attraction", []) or [])
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

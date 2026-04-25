import logging

import requests
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class PerenualHarvester:
    BASE_URL = "https://perenual.com/api"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def harvest_batch(self, page: int = 1):
        """এপিআই লিস্ট থেকে একসাথে অনেকগুলো গাছের ডাটা আনে।"""
        url = f"{self.BASE_URL}/species-list?key={self.api_key}&page={page}"
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                return response.json().get("data", [])
        except Exception as e:
            logger.error(f"Batch fetch failed: {e}")
        return []

    def get_details(self, species_id: int):
        """একটি নির্দিষ্ট গাছের গভীর তথ্য (Care Guide সহ) আনে।"""
        url = f"{self.BASE_URL}/species/details/{species_id}?key={self.api_key}"
        try:
            response = requests.get(url, timeout=15)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Detail fetch failed for ID {species_id}: {e}")
            return None

    def map_to_model(self, data: dict):
        """এপিআই ডাটাকে জ্যাঙ্গো মডেলের ফিল্ডে রূপান্তর করে।"""

        sci_names = data.get("scientific_name", [])
        sci_name = sci_names[0] if sci_names else "Unknown"

        # Sunlight Mapping
        sun_list = [s.lower() for s in data.get("sunlight", [])]
        sunlight = "full_sun"
        if "full shade" in sun_list:
            sunlight = "full_shade"
        elif "part shade" in sun_list:
            sunlight = "partial_sun"

        # Bloom Season Logic
        bloom_months = str(data.get("bloom_time", "")).lower()

        return {
            "common_name": data.get("common_name", "Unknown"),
            "scientific_name": sci_name,
            "plant_type": self._map_plant_type(data.get("cycle", "perennial")),
            "description": data.get("description", ""),
            "main_image_url": data.get("default_image", {}).get("original_url", ""),
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
            "tags": ", ".join(data.get("attraction", []) + data.get("propagation", [])),
        }

    def _map_plant_type(self, cycle):
        cycle = cycle.lower()
        if "perennial" in cycle:
            return "perenial"
        if "annual" in cycle:
            return "annual"
        return "both"

    def download_and_save_image(self, plant_instance, url):
        """ইমেজ ডাউনলোড করে Media ফোল্ডারে সেভ করে।"""
        if not url or "profile/default" in url:  # ডিফল্ট ইমেজ ইগনোর করা
            return
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                # সায়েন্টিফিক নেম দিয়ে ফাইলের নাম বানালে ডুপ্লিকেট হয় না
                fname = f"plant_{plant_instance.id}_{plant_instance.scientific_name.replace(' ', '_')}.jpg"
                plant_instance.image.save(fname, ContentFile(resp.content), save=True)
        except Exception as e:
            logger.error(f"Image download failed for {plant_instance.common_name}: {e}")

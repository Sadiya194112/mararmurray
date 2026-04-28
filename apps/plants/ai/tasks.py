# apps/plants/tasks.py
import logging
from celery import shared_task
from django.db import transaction
from apps.plants.models import Plant
from apps.plants.ai.main import enrich_plant_data # আপনার AI ফাংশন

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def enrich_and_download_task(self, plant_id, api_raw_data):
    """
    ১. AI দিয়ে ডাটা এনরিচ করে।
    ২. ইমেজ ডাউনলোড করে।
    """
    try:
        plant = Plant.objects.get(id=plant_id)
        
        # --- ধাপ ১: AI এনরিচমেন্ট ---
        logger.info(f"🤖 Enriching data with AI for: {plant.common_name}")
        enriched_data = enrich_plant_data(api_raw_data)
        
        # অ্যাটমিক ট্রানজ্যাকশনে ডাটা সেভ করা (নিরাপদ উপায়)
        with transaction.atomic():
            for key, value in enriched_data.items():
                setattr(plant, key, value)
            plant.save()
        
        # --- ধাপ ২: ইমেজ ডাউনলোড (যদি ইউআরএল থাকে) ---
        image_url = api_raw_data.get("main_image_url")
        if image_url and "profile/default" not in image_url:
            import requests
            from django.core.files.base import ContentFile
            
            resp = requests.get(image_url, timeout=30)
            if resp.status_code == 200:
                fname = f"plant_{plant.id}_{plant.scientific_name.replace(' ', '_')}.jpg"
                plant.image.save(fname, ContentFile(resp.content), save=True)
                logger.info(f"📸 Image saved for {plant.common_name}")

        return f"Success: {plant.common_name} enriched and synced."

    except Plant.DoesNotExist:
        logger.error(f"Plant {plant_id} not found.")
    except Exception as e:
        logger.error(f"Enrichment failed for {plant_id}: {e}")
        self.retry(exc=e, countdown=60)

@shared_task
def automated_daily_harvest():
    from django.core.management import call_command
    logger.info("🤖 Starting automated daily plant harvest (10 plants)...")
    call_command('run_harvest', count=30)
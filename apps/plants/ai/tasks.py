import logging

import requests
from celery import shared_task
from django.core.files.base import ContentFile

from apps.gardens.models import Plant

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def download_plant_image_task(self, plant_id, image_url):
    """ব্যাকগ্রাউন্ডে ইমেজ ডাউনলোড করার টাস্ক।"""
    try:
        plant = Plant.objects.get(id=plant_id)
        if not image_url or "profile/default" in image_url:
            return f"No valid URL for plant {plant_id}"

        resp = requests.get(image_url, timeout=30)
        if resp.status_code == 200:
            fname = f"plant_{plant.id}_{plant.scientific_name.replace(' ', '_')}.jpg"
            plant.image.save(fname, ContentFile(resp.content), save=True)
            return f"Successfully saved image for {plant.common_name}"

    except Plant.DoesNotExist:
        logger.error(f"Plant with id {plant_id} not found.")
    except Exception as e:
        logger.error(f"Image sync failed, retrying... Error: {e}")
        # নেটওয়ার্ক এরর হলে আবার ট্রাই করবে
        self.retry(exc=e, countdown=60)

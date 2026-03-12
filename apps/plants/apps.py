from django.apps import AppConfig


class PlantsConfig(AppConfig):
    name = "apps.plants"

    def ready(self):
        # Harvesting is NO LONGER started automatically.
        # Run it manually with:
        #   uv run manage.py start_harvesting
        #   uv run manage.py start_harvesting --days=3 --rate=10
        pass

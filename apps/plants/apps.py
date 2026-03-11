from django.apps import AppConfig
import os

class PlantsConfig(AppConfig):
    name = "apps.plants"

    def ready(self):
        # In Django's dev server, ready() runs twice (once for validation, once for actual run).
        # We only want to start the background thread once.
        # This check helps avoid running twice in that environment.
        is_dev_server = 'runserver' in os.sys.argv
        if is_dev_server and os.environ.get('RUN_MAIN') != 'true':
            return
            
        try:
            from .models import Plant
            from ai_plant_engine.harvester.engine import HarvestEngine
            
            def get_existing_plants():
                return list(Plant.objects.values_list('common_name', flat=True))
                
            def insert_harvested_plants(harvested_data_list):
                print(f"Inserting {len(harvested_data_list)} harvested plants into DB...")
                for data in harvested_data_list:
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
                            "plant_type": data.get("plant_type", ""),
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
                        }
                    )
                print(f"Successfully inserted {len(harvested_data_list)} plants.")
            
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if api_key:
                engine = HarvestEngine(openai_api_key=api_key)
                
                # Start the background task to generate 5 plants per hour for 7 days
                engine.start_background_harvesting(
                    days=7,
                    plants_per_hour=5,
                    insert_callback=insert_harvested_plants,
                    get_existing_plants_callback=get_existing_plants
                )
                print("Started AI Plant Harvest Background Task (7 days, 5 plants/hr).")
        except Exception as e:
            print(f"Could not start AI plant background harvester: {e}")

import json
import os

from django.db.models import Q
from openai import OpenAI

from apps.plants.models import Plant

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class GardenAIService:
    """Service for AI-powered garden analysis and plant suggestions using OpenAI."""

    @staticmethod
    def get_plant_suggestions(preference):
        """
        Get AI suggested plant names based on garden preferences.
        First filters plants from database that match basic criteria,
        then uses AI to select the most suitable ones.

        Args:
            preference: GardenPreference object with garden details

        Returns:
            list: List of suggested plant names from database

        Raises:
            Exception: If OpenAI API call fails
        """
        try:
            # Step 1: Filter plants from database based on preferences
            queryset = Plant.objects.all()

            # Filter by sunlight
            if preference.sunlight:
                sunlight_map = {
                    "full_sun": ["Full Sun", "full sun"],
                    "partial_sun": ["Partial", "partial sun", "Partial Sun"],
                    "full_shade": ["Shade", "full shade", "Full Shade"],
                }
                sunlight_values = sunlight_map.get(preference.sunlight, [])
                if sunlight_values:
                    sunlight_filters = Q()
                    for val in sunlight_values:
                        sunlight_filters |= Q(sunlight__icontains=val)
                    queryset = queryset.filter(sunlight_filters)

            # Filter by garden type (plant type)
            if preference.garden_type:
                type_map = {
                    "vegetable": ["Vegetable", "vegetable"],
                    "flower": ["Flower", "flower"],
                    "herb": ["Herb", "herb"],
                    "mixed": [],  # No filter for mixed
                }
                plant_types = type_map.get(preference.garden_type, [])
                if plant_types:
                    type_filters = Q()
                    for ptype in plant_types:
                        type_filters |= Q(plant_type__icontains=ptype)
                    queryset = queryset.filter(type_filters)

            # Get up to 50 candidate plants to avoid overwhelming AI
            candidate_plants = list(queryset.values_list("common_name", flat=True)[:50])

            if not candidate_plants:
                # Fallback if no plants match basic criteria
                candidate_plants = list(
                    Plant.objects.values_list("common_name", flat=True)[:20]
                )

            # Step 2: Use AI to select the best plants from candidates
            sunlight = (
                preference.get_sunlight_display()
                if hasattr(preference, "get_sunlight_display")
                else preference.sunlight
            )
            garden_type = (
                preference.get_garden_type_display()
                if hasattr(preference, "get_garden_type_display")
                else preference.garden_type
            )
            soil = (
                preference.get_soil_type_display()
                if hasattr(preference, "get_soil_type_display")
                else preference.soil_type
            )

            candidate_list = ", ".join(
                candidate_plants[:30]
            )  # Limit for token efficiency

            prompt = f"""Based on the following garden preferences, select the 6-8 most suitable plants from the provided list:

Garden Preferences:
- Garden Type: {garden_type or "Mixed"}
- Sunlight: {sunlight or "Not specified"}
- Soil Type: {soil or "Not specified"}
- Location: {preference.location or "Not specified"}
- Garden Area: {preference.total_area_sq_ft or "Not specified"} sq ft

Available Plants: {candidate_list}

Please provide only the selected plant names as a simple comma-separated list. Choose plants that best match the garden conditions and type. No descriptions, just names."""

            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful garden planning assistant. Select the most suitable plants from the provided list based on the garden preferences.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=200,
            )

            # Extract plant suggestions
            suggestions_text = response.choices[0].message.content.strip()
            plant_names = [
                name.strip() for name in suggestions_text.split(",") if name.strip()
            ]

            # Ensure all suggested plants exist in our database (double-check)
            valid_plants = []
            for name in plant_names[:8]:  # Limit to 8
                if Plant.objects.filter(common_name__iexact=name).exists():
                    valid_plants.append(name)

            return valid_plants if valid_plants else candidate_plants[:6]

        except Exception as e:
            raise Exception(f"Failed to get AI suggestions: {str(e)}")

    @staticmethod
    def get_preference_display(preference):
        """
        Get human-readable display values for garden preference.

        Args:
            preference: GardenPreference object

        Returns:
            dict: Dictionary with display values
        """
        sunlight = (
            preference.get_sunlight_display()
            if hasattr(preference, "get_sunlight_display")
            else preference.sunlight
        )
        garden_type = (
            preference.get_garden_type_display()
            if hasattr(preference, "get_garden_type_display")
            else preference.garden_type
        )
        soil = (
            preference.get_soil_type_display()
            if hasattr(preference, "get_soil_type_display")
            else preference.soil_type
        )

        return {
            "sunlight": sunlight,
            "garden_type": garden_type,
            "soil_type": soil,
        }

    @staticmethod
    def get_detailed_plant_recommendations(preference):
        """
        Get AI-generated detailed plant recommendations based on garden preferences.
        Uses RAG (Retrieval-Augmented Generation): retrieves real plants from DB,
        augments prompt with actual plant data format, then generates recommendations
        following that exact structure.

        Args:
            preference: GardenPreference object with garden details

        Returns:
            list: List of dictionaries with detailed plant information

        Raises:
            Exception: If OpenAI API call fails
        """
        try:
            # STEP 1: Retrieve real plants from database matching preferences
            queryset = Plant.objects.all()

            # Filter by sunlight
            if preference.sunlight:
                sunlight_map = {
                    "full_sun": ["Full Sun", "full sun"],
                    "partial_sun": ["Partial", "partial sun", "Partial Sun"],
                    "full_shade": ["Shade", "full shade", "Full Shade"],
                }
                sunlight_values = sunlight_map.get(preference.sunlight, [])
                if sunlight_values:
                    sunlight_filters = Q()
                    for val in sunlight_values:
                        sunlight_filters |= Q(sunlight__icontains=val)
                    queryset = queryset.filter(sunlight_filters)

            # Filter by garden type (plant type)
            if preference.garden_type and preference.garden_type != "mixed":
                garden_type_map = {
                    "vegetable": ["Vegetable", "vegetable"],
                    "flower": ["Flower", "flower"],
                    "herb": ["Herb", "herb"],
                }
                plant_types = garden_type_map.get(preference.garden_type, [])
                if plant_types:
                    type_filters = Q()
                    for ptype in plant_types:
                        type_filters |= Q(plant_type__icontains=ptype)
                    queryset = queryset.filter(type_filters)

            # Get 5-8 reference plants for RAG context
            reference_plants = queryset[:8]

            # If not enough matches, get some general plants as fallback
            if reference_plants.count() < 3:
                reference_plants = Plant.objects.all()[:8]

            # STEP 2: Extract and format real plant data for augmentation
            plant_context = []
            for plant in reference_plants:
                plant_dict = {
                    "common_name": plant.common_name,
                    "scientific_name": plant.scientific_name or "",
                    "plant_type": plant.plant_type or "",
                    "description": plant.description or "",
                    "sunlight": plant.sunlight or "",
                    "water": plant.water or "Average",
                    "spacing": plant.spacing or "",
                    "growth_size": plant.growth_size or "",
                    "season": plant.season or "",
                    "difficulty": plant.difficulty or "Moderate",
                    "care_guide": plant.care_guide[:100] if plant.care_guide else "",
                    "tags": plant.tags or "",
                    "bloom_spring": plant.bloom_spring,
                    "bloom_summer": plant.bloom_summer,
                    "bloom_fall": plant.bloom_fall,
                    "bloom_winter": plant.bloom_winter,
                    "propagation": plant.propagation or "",
                    "family": plant.family or "",
                }
                plant_context.append(plant_dict)

            plant_context_json = json.dumps(plant_context, indent=2)

            from apps.gardens.models import GardenProject as GP

            sunlight_display = dict(GP.SUNLIGHT_CHOICES).get(project.sunlight, project.sunlight)
            garden_type_display = dict(GP.GARDEN_TYPE_CHOICES).get(project.garden_type, project.garden_type)
            soil_display = dict(GP.SOIL_CHOICES).get(project.soil_type, project.soil_type)
            colors_str = ", ".join(project.plant_colors) if project.plant_colors else "No preference"

            # STEP 3: Augment prompt with real plant data as examples
            prompt = f"""You are an expert horticulturist. Generate detailed plant recommendations following EXACTLY the same format and structure as these real plants from our database:

REAL PLANT EXAMPLES (follow this exact JSON format):
{plant_context_json}

Based on these garden preferences, generate 10-12 NEW highly detailed plant recommendations in the EXACT same JSON format:

Garden Preferences:
- Garden Type: {garden_type_display or "Mixed"}
- Sunlight: {sunlight_display or "Not specified"}
- Soil Type: {soil_display or "Not specified"}
- Preferred Plant Colors: {colors_str}
- Location: {project.location or "Not specified"}
- Garden Area: {project.total_area_sq_ft or "Not specified"} sq ft

IMPORTANT RULES:
1. Generate NEW plants (not from the examples above)
2. Match the exact field names and structure shown above
3. Ensure all recommendations perfectly match the garden preferences
4. Each field must have a value (use "Not available" if unknown)
5. Return ONLY valid JSON array, no markdown, no extra text, no explanations
6. bloom_* fields must be boolean (true/false)
7. All string fields must be properly formatted

Generate the JSON array now:"""

            # STEP 4: Call OpenAI with augmented prompt
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert horticulturist and garden planning AI. Generate detailed, accurate plant recommendations in perfect JSON format matching the provided examples. Return ONLY valid JSON array.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=3500,
            )

            response_text = response.choices[0].message.content.strip()

            # STEP 5: Parse and validate JSON response
            try:
                # Handle potential markdown code blocks
                if "```json" in response_text:
                    response_text = (
                        response_text.split("```json")[1].split("```")[0].strip()
                    )
                elif "```" in response_text:
                    response_text = (
                        response_text.split("```")[1].split("```")[0].strip()
                    )

                plants_data = json.loads(response_text)

                # Ensure it's a list
                if isinstance(plants_data, dict) and "plants" in plants_data:
                    plants_data = plants_data["plants"]

                if not isinstance(plants_data, list):
                    plants_data = [plants_data]

                # STEP 6: Validate and clean the data following real plant structure
                valid_plants = []
                for plant in plants_data:
                    if isinstance(plant, dict) and "common_name" in plant:
                        common_name = plant.get("common_name", "Unknown Plant")
                        
                        db_plant = Plant.objects.filter(common_name__iexact=common_name).first()
                        main_image_url = None
                        if db_plant:
                            if db_plant.main_image_url:
                                main_image_url = db_plant.main_image_url
                            elif db_plant.image:
                                main_image_url = db_plant.image.url
                                
                        if not main_image_url:
                            main_image_url = f"https://ui-avatars.com/api/?name={common_name.replace(' ', '+')}&background=random&color=fff&size=512"

                        cleaned_plant = {
                            "id": db_plant.id if db_plant else None,
                            "common_name": common_name,
                            "scientific_name": plant.get("scientific_name", ""),
                            "plant_type": plant.get("plant_type", ""),
                            "description": plant.get("description", ""),
                            "image": None,
                            "main_image_url": main_image_url,
                            "sunlight": plant.get("sunlight", sunlight or ""),
                            "water": plant.get("water", "Average"),
                            "spacing": plant.get("spacing", ""),
                            "growth_size": plant.get("growth_size", ""),
                            "season": plant.get("season", ""),
                            "difficulty": plant.get("difficulty", "Moderate"),
                            "care_guide": plant.get("care_guide", ""),
                            "bloom_spring": bool(plant.get("bloom_spring", False)),
                            "bloom_summer": bool(plant.get("bloom_summer", False)),
                            "bloom_fall": bool(plant.get("bloom_fall", False)),
                            "bloom_winter": bool(plant.get("bloom_winter", False)),
                            "shopping_link": None,
                            "tags": plant.get("tags", ""),
                            "family": plant.get("family", ""),
                            "propagation": plant.get("propagation", ""),
                            "ai_generated": True,
                        }
                        valid_plants.append(cleaned_plant)

                return valid_plants[:12]  # Limit to 12 recommendations

            except json.JSONDecodeError as json_err:
                raise Exception(
                    f"Failed to parse AI response as JSON: {str(json_err)}. Response: {response_text[:500]}"
                )

        except Exception as e:
            raise Exception(f"Failed to get AI plant recommendations: {str(e)}")

    @staticmethod
    def get_ai_plant_detail(preference, plant_name):
        """
        Get detailed information for a specific AI-generated plant recommendation.
        Uses RAG: retrieves reference plants, then generates full details for the selected plant.

        Args:
            preference: GardenPreference object with garden details
            plant_name: Name of the plant to get details for

        Returns:
            dict: Detailed plant information

        Raises:
            Exception: If OpenAI API call fails
        """
        try:
            # STEP 1: Retrieve reference plants from database
            queryset = Plant.objects.all()

            # Filter by sunlight
            if preference.sunlight:
                sunlight_map = {
                    "full_sun": ["Full Sun", "full sun"],
                    "partial_sun": ["Partial", "partial sun", "Partial Sun"],
                    "full_shade": ["Shade", "full shade", "Full Shade"],
                }
                sunlight_values = sunlight_map.get(preference.sunlight, [])
                if sunlight_values:
                    sunlight_filters = Q()
                    for val in sunlight_values:
                        sunlight_filters |= Q(sunlight__icontains=val)
                    queryset = queryset.filter(sunlight_filters)

            # Filter by garden type
            if preference.garden_type and preference.garden_type != "mixed":
                garden_type_map = {
                    "vegetable": ["Vegetable", "vegetable"],
                    "flower": ["Flower", "flower"],
                    "herb": ["Herb", "herb"],
                }
                plant_types = garden_type_map.get(preference.garden_type, [])
                if plant_types:
                    type_filters = Q()
                    for ptype in plant_types:
                        type_filters |= Q(plant_type__icontains=ptype)
                    queryset = queryset.filter(type_filters)

            # Get reference plants for context
            reference_plants = queryset[:5]
            if reference_plants.count() < 2:
                reference_plants = Plant.objects.all()[:5]

            # Extract reference plant data
            plant_context = []
            for plant in reference_plants:
                plant_dict = {
                    "common_name": plant.common_name,
                    "scientific_name": plant.scientific_name or "",
                    "plant_type": plant.plant_type or "",
                    "sunlight": plant.sunlight or "",
                    "water": plant.water or "Average",
                    "spacing": plant.spacing or "",
                    "growth_size": plant.growth_size or "",
                    "season": plant.season or "",
                    "difficulty": plant.difficulty or "Moderate",
                    "care_guide": plant.care_guide[:100] if plant.care_guide else "",
                    "tags": plant.tags or "",
                    "bloom_spring": plant.bloom_spring,
                    "bloom_summer": plant.bloom_summer,
                    "bloom_fall": plant.bloom_fall,
                    "bloom_winter": plant.bloom_winter,
                    "propagation": plant.propagation or "",
                    "family": plant.family or "",
                }
                plant_context.append(plant_dict)

            plant_context_json = json.dumps(plant_context, indent=2)

            # Get preference display values
            sunlight = (
                preference.get_sunlight_display()
                if hasattr(preference, "get_sunlight_display")
                else preference.sunlight
            )
            garden_type = (
                preference.get_garden_type_display()
                if hasattr(preference, "get_garden_type_display")
                else preference.garden_type
            )
            soil = (
                preference.get_soil_type_display()
                if hasattr(preference, "get_soil_type_display")
                else preference.soil_type
            )

            # Generate detailed information for the specific plant
            prompt = f"""You are an expert horticulturist. Generate detailed information for '{plant_name}' following EXACTLY the same format as these real plants:

REAL PLANT EXAMPLES (follow this exact JSON format):
{plant_context_json}

Generate detailed information for '{plant_name}' in the EXACT same JSON format as shown above. Consider these garden conditions:
- Garden Type: {garden_type or "Mixed"}
- Sunlight: {sunlight or "Not specified"}
- Soil Type: {soil or "Not specified"}
- Location: {preference.location or "Not specified"}

Return ONLY a single JSON object (not an array) with all fields populated. Explain why this plant is suitable for the given conditions in the description field."""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert horticulturist. Generate detailed, accurate plant information in perfect JSON format matching the provided examples.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1500,
            )

            response_text = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                # Handle markdown code blocks
                if "```json" in response_text:
                    response_text = (
                        response_text.split("```json")[1].split("```")[0].strip()
                    )
                elif "```" in response_text:
                    response_text = (
                        response_text.split("```")[1].split("```")[0].strip()
                    )

                plant_data = json.loads(response_text)

                # Ensure it's a single plant object
                if isinstance(plant_data, list):
                    plant_data = plant_data[0]

                # Validate and clean the data
                if isinstance(plant_data, dict) and "common_name" in plant_data:
                    common_name = plant_data.get("common_name", plant_name)
                    db_plant = Plant.objects.filter(common_name__iexact=common_name).first()
                    main_image_url = None
                    if db_plant:
                        if db_plant.main_image_url:
                            main_image_url = db_plant.main_image_url
                        elif db_plant.image:
                            main_image_url = db_plant.image.url
                            
                    if not main_image_url:
                        main_image_url = f"https://ui-avatars.com/api/?name={common_name.replace(' ', '+')}&background=random&color=fff&size=512"

                    cleaned_plant = {
                        "id": db_plant.id if db_plant else None,
                        "common_name": common_name,
                        "scientific_name": plant_data.get("scientific_name", ""),
                        "plant_type": plant_data.get("plant_type", ""),
                        "description": plant_data.get("description", ""),
                        "image": None,
                        "main_image_url": main_image_url,
                        "sunlight": plant_data.get("sunlight", sunlight or ""),
                        "water": plant_data.get("water", "Average"),
                        "spacing": plant_data.get("spacing", ""),
                        "growth_size": plant_data.get("growth_size", ""),
                        "season": plant_data.get("season", ""),
                        "difficulty": plant_data.get("difficulty", "Moderate"),
                        "care_guide": plant_data.get("care_guide", ""),
                        "bloom_spring": bool(plant_data.get("bloom_spring", False)),
                        "bloom_summer": bool(plant_data.get("bloom_summer", False)),
                        "bloom_fall": bool(plant_data.get("bloom_fall", False)),
                        "bloom_winter": bool(plant_data.get("bloom_winter", False)),
                        "shopping_link": None,
                        "tags": plant_data.get("tags", ""),
                        "family": plant_data.get("family", ""),
                        "propagation": plant_data.get("propagation", ""),
                    }
                    return cleaned_plant

                raise Exception("Invalid plant data structure in AI response")

            except json.JSONDecodeError as json_err:
                raise Exception(
                    f"Failed to parse plant details as JSON: {str(json_err)}"
                )

        except Exception as e:
            raise Exception(f"Failed to get AI plant details: {str(e)}")

    @staticmethod
    def get_ai_plant_summary(preference, plant_name):
        """
        Get quick summary/preview for a specific AI-generated plant recommendation.
        Returns limited fields for quick preview before viewing full details.
        Uses RAG with reference plants.

        Args:
            preference: GardenPreference object with garden details
            plant_name: Name of the plant to get summary for

        Returns:
            dict: Summary plant information with limited fields

        Raises:
            Exception: If OpenAI API call fails
        """
        try:
            # STEP 1: Retrieve reference plants from database
            queryset = Plant.objects.all()

            # Filter by sunlight
            if preference.sunlight:
                sunlight_map = {
                    "full_sun": ["Full Sun", "full sun"],
                    "partial_sun": ["Partial", "partial sun", "Partial Sun"],
                    "full_shade": ["Shade", "full shade", "Full Shade"],
                }
                sunlight_values = sunlight_map.get(preference.sunlight, [])
                if sunlight_values:
                    sunlight_filters = Q()
                    for val in sunlight_values:
                        sunlight_filters |= Q(sunlight__icontains=val)
                    queryset = queryset.filter(sunlight_filters)

            # Filter by garden type
            if preference.garden_type and preference.garden_type != "mixed":
                garden_type_map = {
                    "vegetable": ["Vegetable", "vegetable"],
                    "flower": ["Flower", "flower"],
                    "herb": ["Herb", "herb"],
                }
                plant_types = garden_type_map.get(preference.garden_type, [])
                if plant_types:
                    type_filters = Q()
                    for ptype in plant_types:
                        type_filters |= Q(plant_type__icontains=ptype)
                    queryset = queryset.filter(type_filters)

            # Get reference plants
            reference_plants = queryset[:3]
            if reference_plants.count() < 1:
                reference_plants = Plant.objects.all()[:3]

            # Extract summary plant data
            plant_context = []
            for plant in reference_plants:
                plant_dict = {
                    "common_name": plant.common_name,
                    "scientific_name": plant.scientific_name or "",
                    "sunlight": plant.sunlight or "",
                    "water": plant.water or "Average",
                    "spacing": plant.spacing or "",
                    "growth_size": plant.growth_size or "",
                }
                plant_context.append(plant_dict)

            plant_context_json = json.dumps(plant_context, indent=2)

            # Get preference display values
            sunlight = (
                preference.get_sunlight_display()
                if hasattr(preference, "get_sunlight_display")
                else preference.sunlight
            )
            garden_type = (
                preference.get_garden_type_display()
                if hasattr(preference, "get_garden_type_display")
                else preference.garden_type
            )

            # Generate summary for the plant
            prompt = f"""Generate a quick summary for '{plant_name}' following this format based on these real plants:

REAL PLANT SUMMARIES (follow this exact format):
{plant_context_json}

Generate a summary for '{plant_name}' with these fields ONLY:
- common_name: Plant name
- scientific_name: Scientific name
- sunlight: Required sunlight (Full Sun/Partial Sun/Full Shade)
- water: Water needs (Low/Average/High)
- spacing: Spacing in inches/cm between plants
- growth_size: Final size (Small/Medium/Large)

Return ONLY a JSON object (not an array). Ensure all values match the format shown above."""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a garden expert. Generate concise plant summaries in JSON format.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.6,
                max_tokens=500,
            )

            response_text = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                # Handle markdown code blocks
                if "```json" in response_text:
                    response_text = (
                        response_text.split("```json")[1].split("```")[0].strip()
                    )
                elif "```" in response_text:
                    response_text = (
                        response_text.split("```")[1].split("```")[0].strip()
                    )

                plant_data = json.loads(response_text)

                # Ensure it's a single plant object
                if isinstance(plant_data, list):
                    plant_data = plant_data[0]

                # Validate and clean the data - summary fields only
                if isinstance(plant_data, dict) and "common_name" in plant_data:
                    common_name = plant_data.get("common_name", plant_name)
                    db_plant = Plant.objects.filter(common_name__iexact=common_name).first()
                    plant_image = None
                    if db_plant:
                        if db_plant.main_image_url:
                            plant_image = db_plant.main_image_url
                        elif db_plant.image:
                            plant_image = db_plant.image.url
                            
                    if not plant_image:
                        plant_image = f"https://ui-avatars.com/api/?name={common_name.replace(' ', '+')}&background=random&color=fff&size=512"

                    summary_plant = {
                        "common_name": common_name,
                        "scientific_name": plant_data.get("scientific_name", ""),
                        "plant_image": plant_image,
                        "sunlight": plant_data.get("sunlight", sunlight or ""),
                        "water": plant_data.get("water", "Average"),
                        "spacing": plant_data.get("spacing", ""),
                        "growth_size": plant_data.get("growth_size", ""),
                    }
                    return summary_plant

                raise Exception("Invalid plant summary structure in AI response")

            except json.JSONDecodeError as json_err:
                raise Exception(
                    f"Failed to parse plant summary as JSON: {str(json_err)}"
                )

        except Exception as e:
            raise Exception(f"Failed to get AI plant summary: {str(e)}")

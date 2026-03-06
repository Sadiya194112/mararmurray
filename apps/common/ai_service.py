import os

import openai

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")


class GardenAIService:
    """Service for AI-powered garden analysis and plant suggestions using OpenAI."""

    @staticmethod
    def get_plant_suggestions(preference):
        """
        Get AI suggested plant names based on garden preferences.

        Args:
            preference: GardenPreference object with garden details

        Returns:
            list: List of suggested plant names

        Raises:
            Exception: If OpenAI API call fails
        """
        try:
            # Prepare preference description for OpenAI
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

            prompt = f"""Based on the following garden preferences, suggest 6-8 plant names that would be suitable:
- Garden Type: {garden_type or "Mixed"}
- Sunlight: {sunlight or "Not specified"}
- Soil Type: {soil or "Not specified"}
- Location: {preference.location or "Not specified"}
- Garden Area: {preference.total_area_sq_ft or "Not specified"} sq ft

Please provide only the common plant names (e.g., Tomato, Basil, Rose) as a simple comma-separated list. No descriptions, just names."""

            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful garden planning assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=200,
            )

            # Extract plant suggestions
            suggestions_text = response.choices[0].message.content.strip()
            plant_names = [name.strip() for name in suggestions_text.split(",")]

            return plant_names

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

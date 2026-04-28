import json
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def enrich_plant_data(plant_input: dict) -> dict:
    """
    Takes plant data as input and uses OpenAI GPT-4o to generate/enrich
    missing or incomplete fields with best-quality botanical knowledge.

    Required inputs used: common_name, scientific_name, plant_type,
    description, sunlight, water — plus any already-provided values
    for the output fields (used as hints).

    Returns a dict with all required output fields filled in.
    """

    # Smartly handle missing bloom seasons
    b_spring = plant_input.get("bloom_spring", False)
    b_summer = plant_input.get("bloom_summer", False)
    b_fall = plant_input.get("bloom_fall", False)
    b_winter = plant_input.get("bloom_winter", False)

    # If all are False, it usually means the API had no data (or it's non-flowering).
    # We pass empty strings so the AI isn't biased by the 'False' defaults and figures it out itself.
    if not any([b_spring, b_summer, b_fall, b_winter]):
        b_spring = b_summer = b_fall = b_winter = ""

    # Build a focused prompt with only the fields needed for context
    context_fields = {
        "common_name": plant_input.get("common_name", ""),
        "scientific_name": plant_input.get("scientific_name", ""),
        "plant_type": plant_input.get("plant_type", ""),
        "description": plant_input.get("description", ""),
        "sunlight": plant_input.get("sunlight", ""),
        "water": plant_input.get("water", ""),
        "tags": plant_input.get("tags", ""),
        # Pass existing values as hints — model will use or improve them
        "hint_soil_type": plant_input.get("soil_type", ""),
        "hint_garden_type": plant_input.get("garden_type", ""),
        "hint_spacing": plant_input.get("spacing", ""),
        "hint_growth_size": plant_input.get("growth_size", ""),
        "hint_season": plant_input.get("season", ""),
        "hint_care_guide": plant_input.get("care_guide", ""),
        "hint_bloom_spring": b_spring,
        "hint_bloom_summer": b_summer,
        "hint_bloom_fall": b_fall,
        "hint_bloom_winter": b_winter,
        "hint_family": plant_input.get("family", ""),
        "hint_propagation": plant_input.get("propagation", ""),
        "hint_color": plant_input.get("color", ""),
        "hint_shopping_link": plant_input.get("shopping_link", ""),
    }

    system_prompt = """You are an expert botanist and horticulturalist with deep knowledge of plants, 
their care requirements, growth habits, and botanical classification. 

Your task is to generate accurate, detailed plant information based on the plant details provided.
You MUST return a valid JSON object — nothing else, no markdown, no explanation.

Rules:
- soil_type: must be exactly one of: sandy, clay, loam, not_sure
- garden_type: must be exactly one of: flower_garden, vegetable_garden, herb_garden, mixed_garden
- bloom_spring, bloom_summer, bloom_fall, bloom_winter: must be boolean (true/false)
- shopping_link: return a real Amazon or reputable seed/nursery URL if known, otherwise return ""
- care_guide: write a thorough 3-5 sentence care guide
- spacing: include units (e.g., "12-18 inches")
- growth_size: include units (e.g., "2-3 feet tall, 1-2 feet wide")
- season: describe the growing/blooming season clearly
- propagation: describe the best propagation methods
- family: provide the botanical family name
- color: provide the primary flower or foliage color (e.g., "Yellow", "Green and White")
- If hint values are already correct and specific, preserve or improve them.
"""

    user_prompt = f"""Here is the plant data:

{json.dumps(context_fields, indent=2)}

Based on this information, return a JSON object with EXACTLY these keys and no others:
{{
  "soil_type": "sandy | clay | loam | not_sure",
  "garden_type": "flower_garden | vegetable_garden | herb_garden | mixed_garden",
  "spacing": "string with units",
  "growth_size": "string with units",
  "season": "string",
  "care_guide": "string (3-5 sentences)",
  "bloom_spring": true or false,
  "bloom_summer": true or false,
  "bloom_fall": true or false,
  "bloom_winter": true or false,
  "family": "string (botanical family)",
  "propagation": "string",
  "color": "string",
  "shopping_link": "string (URL or empty string)"
}}

Return ONLY the JSON object. No markdown, no explanation."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,  # Low temp for factual accuracy
        response_format={"type": "json_object"},  # Enforce JSON output
    )

    raw_output = response.choices[0].message.content.strip()

    try:
        result = json.loads(raw_output)
    except json.JSONDecodeError as e:
        raise ValueError(f"OpenAI returned invalid JSON: {e}\nRaw output:\n{raw_output}")

    # --- Validate and normalize required fields ---
    required_keys = [
        "soil_type", "garden_type", "spacing", "growth_size",
        "season", "care_guide", "bloom_spring", "bloom_summer",
        "bloom_fall", "bloom_winter", "family", "propagation", "color", "shopping_link"
    ]

    missing = [k for k in required_keys if k not in result]
    if missing:
        raise ValueError(f"OpenAI response missing required fields: {missing}")

    # Normalize booleans (model might return strings)
    for bool_field in ("bloom_spring", "bloom_summer", "bloom_fall", "bloom_winter"):
        val = result[bool_field]
        if isinstance(val, str):
            result[bool_field] = val.strip().lower() in ("true", "1", "yes")
        else:
            result[bool_field] = bool(val)

    # Validate enum fields
    valid_soil = {"sandy", "clay", "loam", "not_sure"}
    valid_garden = {"flower_garden", "vegetable_garden", "herb_garden", "mixed_garden"}

    if result["soil_type"] not in valid_soil:
        result["soil_type"] = "not_sure"

    if result["garden_type"] not in valid_garden:
        result["garden_type"] = "mixed_garden"

    return result


# ── Example usage ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_plant = {
        "common_name": "Lavender",
        "scientific_name": "Lavandula angustifolia",
        "plant_type": "perennial",
        "description": "A fragrant perennial herb with purple flower spikes, widely used in gardens and aromatherapy.",
        "main_image_url": "",
        "sunlight": "full_sun",
        "water": "low",
        "spacing": "",           # empty — will be filled by AI
        "soil_type": "",         # empty — will be filled by AI
        "garden_type": "",       # empty — will be filled by AI
        "growth_size": "",
        "season": "",
        "difficulty": "easy",
        "care_guide": "",
        "bloom_spring": "",
        "bloom_summer": "",
        "bloom_fall": "",
        "bloom_winter": "",
        "shopping_link": "",
        "tags": "fragrant, drought-tolerant, pollinator-friendly",
        "family": "",
        "propagation": "",
    }

    enriched = enrich_plant_data(sample_plant)
    print(json.dumps(enriched, indent=2))
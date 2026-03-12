import os
import json
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def get_missing_plant_info(provided_data: dict, missing_keys: list) -> dict:
    """
    Takes provided plant data and a list of missing keys, 
    and returns a JSON object with only the missing keys filled.
    """
    
    system_instruction = """
    You are a botanical data assistant. The user will provide existing information about a plant and a list of requested missing keys.
    Your task is to deduce or retrieve the accurate botanical data for those missing keys based on the plant's identity.
    
    Rules:
    1. Output ONLY a valid JSON object.
    2. The JSON must contain ONLY the keys requested by the user. Do not include the original data.
    3. For bloom seasons (e.g., bloom_spring), use boolean values (true/false). Important: For conifers, ferns, and non-flowering plants, treat their active cone-producing, sporing, or pollination season as their 'bloom' season.
    4. For tags, use an array of descriptive strings.
    """

    user_prompt = f"""
    Based on the following plant data:
    {json.dumps(provided_data)}

    Please generate a JSON object containing ONLY the accurate values for the following missing keys:
    {json.dumps(missing_keys)}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        temperature= 0.2,
    )

    return json.loads(response.choices[0].message.content)




def encode_image(image_path: str) -> str:
    """Helper function to convert an image to a base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_image_quality(image_path: str) -> dict:
    """
    Analyzes an image for quality issues (lighting, blur, etc.) 
    and returns a JSON object formatted for the UI.
    """
    base64_image = encode_image(image_path)
    
    system_instruction = """
    You are an expert photography and UI assistant. Your job is to analyze uploaded photos for quality issues before they are accepted by the system.
    Evaluate the image specifically looking for:
    1. Underexposure (Too Dark)
    2. Overexposure (Too Bright)
    3. Blurriness or lack of focus

    You must return ONLY a JSON object with the following structure:
    {
        "is_good_quality": boolean, // true if the photo is fine, false if there are issues
        "issues": [
            // Leave this array empty if is_good_quality is true. Otherwise, populate it:
            {
                "issue_type": "Lighting Too Dark" | "Lighting Too Bright" | "Blurry Photo",
                "description": "A short, user-friendly sentence explaining the problem.",
                "suggestion": "A short, actionable tip with an icon (e.g., 'Take photo during daytime or turn on more lights')"
            }
        ]
    }
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_instruction},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": "Please analyze this image's quality."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        temperature=0.4, 
    )

    return json.loads(response.choices[0].message.content)


dynamic_input = {
   "common_name": "European Silver Fir",
   "scientific_name": "Abies alba",
   "plant_type": "tree",
   "description": "European Silver Fir (Abies alba) is an amazing coniferous species native to mountainous regions of central Europe and the Balkans. It is an evergreen tree with a narrow, pyramidal shape and long, soft needles. Its bark is scaly grey-brown and its branches are highly ornamental due to its conical-shaped silver-tinged needles. It is pruned for use as an ornamental evergreen hedging and screening plant, and is also popular for use as a Christmas tree. Young trees grow quickly and have strong, flexible branches which makes them perfect for use as windbreaks. The European Silver Fir is an impressive species, making it ideal for gardens and public spaces.",
   "main_image_url": "https://s3.us-central-1.wasabisys.com/perenual/species_image/1_abies_alba/regular/1536px-Abies_alba…,",
   "sunlight": "full sun",
   "water": "Frequent",
   "spacing": "Check manual guide",
   "growth_size": "60-60 feet",
   "season": "Perennial",
   "difficulty": "Medium",
   "care_guide": "European Silver Fir (Abies alba) is an amazing coniferous species native to mountainous regions of central Europe and the Balkans. It is an evergreen tree with a narrow, pyramidal shape and long, soft needles. Its bark is scaly grey-brown and its branches are highly ornamental due to its conical-shaped silver-tinged needles. It is pruned for use as an ornamental evergreen hedging and screening plant, and is also popular for use as a Christmas tree. Young trees grow quickly and have strong, flexible branches which makes them perfect for use as windbreaks. The European Silver Fir is an impressive species, making it ideal for gardens and public spaces.",
   "family": "Pinaceae",
   "propagation": "Grafting Propagation, Seed Propagation, Tissue Culture, Cutting, Air Layering Propagation, Layering Propagation"

}

keys_to_fill = [
    "bloom_spring", 
    "bloom_summer", 
    "bloom_fall", 
    "bloom_winter", 
    "tags"
]


def get_plant_recommendations(user_criteria: dict) -> dict:
    """
    Takes user garden criteria and returns a JSON object containing 
    a list of recommended plants formatted strictly to the requested UI fields.
    """
    
    system_instruction = """
    You are an expert horticulturist, landscape architect, and spatial planner. 
    The user will provide their garden's criteria, including climate data (location, latitude/longitude), sunlight, soil type, preferred colors, and strict space constraints.

    Your rules:
    1. Recommend 1 to 6 plants that will absolutely thrive in the given climate and soil conditions.
    2. STRICT SPATIAL RULE: The mature growth size of the plants MUST NOT exceed the user's provided 'height_ft' and 'width_ft'.
    3. Return ONLY a valid JSON object.

    You must use exactly this JSON structure and no other fields:
    {
        "recommended_plants": [
            {
                "name": "Common Plant Name",
                "spacing": "eg., '24-36 inches apart'",
                "growth_size": "e.g., '4-6 feet tall'"
            }
        ]
    }
    """

    user_prompt = f"""
    Please recommend 1-6 plants based on the all the following garden criteria, preferences, and strict spatial constraints:
    {json.dumps(user_criteria, indent=2)}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
    )

    return json.loads(response.choices[0].message.content)


user_questionnaire_answers = {
    "location": "San Diego, CA (Zone 10a)",
    "latitude": 40.7128,
	"longitude": -74.0060,
    "sunlight": "Full Sun",
    "soil_type": "Loam",
    "garden_type": "Mixed Garden",
    "total_area_sq_ft": 500,
	"height_ft": 5,
	"width_ft": 10,
    "preferred_colors": ["Pink", "Purple", "White"]
}


# recommendations = get_plant_recommendations(user_questionnaire_answers)
# print(json.dumps(recommendations, indent=4))

# missing_data_json = get_missing_plant_info(dynamic_input, keys_to_fill)
# print(json.dumps(missing_data_json, indent=4))

# result = analyze_image_quality("dark.jpg")
# print(json.dumps(result, indent=4))
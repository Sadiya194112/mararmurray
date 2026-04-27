import base64
import io
import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIC_AVAILABLE = True
except ImportError:
    HEIC_AVAILABLE = False


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
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    return json.loads(response.choices[0].message.content)


def encode_image(image_path: str) -> tuple[str, str]:
    """
    Converts an image to a base64 string.
    Handles HEIC/HEIF by converting to JPEG in memory first.
    Returns a tuple of (base64_string, media_type).
    """
    ext = image_path.lower().split(".")[-1]

    if ext in ("heic", "heif"):
        if not HEIC_AVAILABLE:
            raise RuntimeError(
                "HEIC/HEIF images are not supported. "
                "Install pillow-heif: pip install pillow-heif"
            )
        # Open HEIC and convert to JPEG in memory — API doesn't accept HEIC directly
        image = Image.open(image_path)
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=95)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8"), "image/jpeg"

    # Standard formats (JPEG, PNG, WEBP, GIF)
    format_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
    }
    media_type = format_map.get(ext, "image/jpeg")

    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8"), media_type


def encode_image(image_path: str) -> tuple[str, str]:
    """
    Converts an image to a base64 string.
    Handles HEIC/HEIF by converting to JPEG in memory first.
    Returns a tuple of (base64_string, media_type).
    """
    ext = image_path.lower().split(".")[-1]

    if ext in ("heic", "heif"):
        if not HEIC_AVAILABLE:
            raise RuntimeError(
                "HEIC/HEIF images are not supported. "
                "Install pillow-heif: pip install pillow-heif"
            )
        # Open HEIC and convert to JPEG in memory — API doesn't accept HEIC directly
        image = Image.open(image_path)
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=95)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8"), "image/jpeg"

    # Standard formats (JPEG, PNG, WEBP, GIF)
    format_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
    }
    media_type = format_map.get(ext, "image/jpeg")

    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8"), media_type


# ── Update analyze_image_quality to use the new encode_image ─────────────────
def analyze_image_quality(image_path: str) -> dict:
    """
    Analyzes image quality with balanced thresholds.
    Supports JPEG, PNG, WEBP, GIF, and HEIC/HEIF formats.
    """
    # Validate file extension upfront
    ext = image_path.lower().split(".")[-1]
    supported = {"jpg", "jpeg", "png", "webp", "gif", "heic", "heif"}
    if ext not in supported:
        raise ValueError(
            f"Unsupported file format: .{ext}. "
            f"Supported formats: {', '.join(sorted(supported)).upper()}"
        )

    base64_image, media_type = encode_image(image_path)  # ← now returns both values

    system_instruction = """
    You are a strict but fair image quality analyst for a plant/garden photo submission system.

    YOUR CORE TASK:
    Determine if the submitted image is genuinely usable for identifying and analyzing a plant or garden subject.

    QUALITY DEFINITIONS — apply these precisely:
    - "excellent"  → Sharp focus, good lighting, subject clearly visible. No meaningful issues.
    - "good"       → Subject is clearly identifiable. Minor imperfections (slight edge blur, slight dim/bright). Fully usable.
    - "acceptable" → Subject is visible and identifiable despite some flaws (moderate blur in bg, uneven light). Still usable.
    - "poor"       → Subject is NOT clearly identifiable. Examples: entire image is blurry/out-of-focus,
                     image is too dark to see subject, severely overexposed with no detail. REJECT these.

    BLUR RULES (critical — apply carefully):
    - Background bokeh only, subject sharp → "good" or "excellent"
    - Slight blur on subject edges, center sharp → "good"
    - Noticeable blur on subject but still identifiable → "acceptable"
    - Entire image is blurry / no area is in focus / subject unrecognizable → "poor" ← REJECT

    is_acceptable MAPPING (enforce strictly):
    - "excellent"  → is_acceptable: true
    - "good"       → is_acceptable: true
    - "acceptable" → is_acceptable: true
    - "poor"       → is_acceptable: false

    ISSUES RULES:
    - Always include at least 1 issue entry describing what you observed, even for excellent images.
    - For each issue, severity must match reality: don't call a fully-blurred image "moderate" — that is "severe".
    - severity_level at the top level = the highest severity found among all issues.

    Return ONLY this exact JSON:
    {
        "is_acceptable": boolean,
        "overall_quality": "excellent" | "good" | "acceptable" | "poor",
        "severity_level": "none" | "minor" | "moderate" | "severe",
        "issues": [
            {
                "issue_type": "Lighting Too Dark" | "Lighting Too Bright" | "Uneven Lighting" | "Blurry Focus" | "Motion Blur" | "Other",
                "severity": "minor" | "moderate" | "severe",
                "description": "Clear, user-friendly sentence describing the specific problem observed.",
                "suggestion": "Short, actionable tip for the user to fix this next time.",
                "impact": boolean
            }
        ]
    }
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_instruction},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Carefully analyze this plant/garden image. "
                            "Check if the subject is actually in focus and identifiable. "
                            "If the entire image is blurry with no sharp area, mark it as poor quality and reject it. "
                            "Be accurate — do not pass images where the subject cannot be identified."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{base64_image}",  # ← dynamic media type
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        temperature=0.3,
    )

    result = json.loads(response.choices[0].message.content)

    # Safety net 1: enforce is_acceptable from overall_quality
    result["is_acceptable"] = result.get("overall_quality", "poor") != "poor"

    # Safety net 2: guarantee issues array is never empty
    if not result.get("issues"):
        quality = result.get("overall_quality", "poor")
        result["issues"] = [
            {
                "issue_type": "Other",
                "severity": "severe" if quality == "poor" else "minor",
                "description": (
                    "The image is not usable. Please retake with the subject in clear focus."
                    if quality == "poor"
                    else "The image looks good overall with no major issues detected."
                ),
                "suggestion": "Ensure the subject is sharp, well-lit, and fills most of the frame.",
                "impact": quality == "poor",
            }
        ]

    return result


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
    "propagation": "Grafting Propagation, Seed Propagation, Tissue Culture, Cutting, Air Layering Propagation, Layering Propagation",
}

keys_to_fill = ["bloom_spring", "bloom_summer", "bloom_fall", "bloom_winter", "tags"]


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
            {"role": "user", "content": user_prompt},
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
    "preferred_colors": ["Pink", "Purple", "White"],
}


# recommendations = get_plant_recommendations(user_questionnaire_answers)
# print(json.dumps(recommendations, indent=4))

# missing_data_json = get_missing_plant_info(dynamic_input, keys_to_fill)
# print(json.dumps(missing_data_json, indent=4))

result = analyze_image_quality("background 5.HEIC")
print(json.dumps(result, indent=4))

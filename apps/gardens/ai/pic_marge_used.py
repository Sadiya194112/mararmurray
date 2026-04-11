import io
import os

from django.core.files.base import ContentFile
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image


def create_garden_mockup(background_path, plants_data):
    """
    ইউজার থেকে পাওয়া স্পেসিফিক পজিশন অনুযায়ী এআই মকআপ তৈরি করে।
    """
    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    try:
        background_img = Image.open(background_path)
        plant_images = [Image.open(p["path"]) for p in plants_data]
    except FileNotFoundError as e:
        print(f"Error finding image: {e}")
        return None

    # HIGHLIGHT: পজিশনিং তথ্য ডাইনামিক ভাবে তৈরি করা
    positioning_info = "\n".join(
        [
            f"Plant {i + 1}: Position ({p['x']}, {p['y']}) on canvas, Scale: {p['scale']}x"
            for i, p in enumerate(plants_data)
        ]
    )

    prompt = (
        "You are an expert garden visualization AI. Your task is to create a realistic preview of how selected plants and flowers will look when placed in the user's garden photo. "
        "Follow these rules carefully: "
        "1. BASE IMAGE PRESERVATION & ENHANCEMENT: Treat the first image as the main garden scene. Keep its layout, structures, and existing elements unchanged. "
        "You may slightly enhance the image quality (lighting balance, color clarity, sharpness) only if needed to improve realism, but do not alter the actual design or content of the garden. "
        "2. PLANT POSITIONING: Place plants according to these specifications:\n"
        + positioning_info
        + "\n"
        "Where (0, 0) is top-left and (1, 1) is bottom-right of the canvas. Use the scale values to adjust plant sizes appropriately. "
        "3. CLEAN PLANT EXTRACTION: Remove any background from the provided plant images. Only the plant itself should be used, without original walls, pots, or distractions. "
        "4. REALISTIC SCALE & PERSPECTIVE: Adjust the size, depth, and angle of each plant based on where it is placed (foreground, midground, background). "
        "Ensure correct perspective so the plants blend naturally into the scene. "
        "5. LIGHTING, SHADOW & BLENDING: Match the lighting conditions of the garden photo (sun direction, brightness, color tone). "
        "Add realistic shadows and ensure the base of each plant blends smoothly into the soil, grass, or ground surface. "
        "6. OVERALL REALISM GOAL: The final image should look like a real photograph of the garden after planting, helping the user clearly visualize the outcome before actual planting. "
    )

    request_contents = [prompt, background_img] + plant_images

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=request_contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="16:9"),
            ),
        )

        for part in response.parts:
            if part.inline_data:
                from PIL import Image as PILImage

                temp_image = PILImage.open(io.BytesIO(part.inline_data.data))
                buffer = io.BytesIO()
                temp_image.save(buffer, format="JPEG")
                return ContentFile(buffer.getvalue(), name="ai_garden_render.jpg")
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

import io
import json
import os
from django.core.files.base import ContentFile
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

# এআই কাউন্টিং মডেল লিস্ট
COUNTING_MODELS = [
    "gemini-3-pro-preview",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash-preview-09-2025",
    "gemini-2.5-flash-lite-preview-09-2025",
]

def build_plant_definitions(plants_data):
    """গাছের ডাটা গুছিয়ে এআই-এর জন্য ডেফিনিশন তৈরি করে"""
    if isinstance(plants_data[0], dict):
        return [
            {
                "label": plant.get("label", f"Plant {index + 1}"),
                "path": plant["path"],
                "x": plant.get("x", 0.5),
                "y": plant.get("y", 0.5),
                "scale": plant.get("scale", 1.0),
            }
            for index, plant in enumerate(plants_data)
        ]

    return [
        {
            "label": f"Plant {index + 1}",
            "path": path,
            "x": 0.5,
            "y": 0.5,
            "scale": 1.0,
        }
        for index, path in enumerate(plants_data)
    ]

def estimate_plant_counts(client, rendered_image_path, plant_definitions):
    """জেনারেটেড ছবিতে কয়টি গাছ আছে তা এআই দিয়ে ভেরিফাই করে"""
    try:
        rendered_image = Image.open(rendered_image_path)
        reference_images = [Image.open(plant["path"]) for plant in plant_definitions]
    except FileNotFoundError as e:
        print(f"Error finding image for count analysis: {e}")
        return None

    labels = ", ".join(plant["label"] for plant in plant_definitions)
    counting_prompt = (
        "You are an expert image analyst counting elements in a modified photo.\n"
        "The first image is the final generated garden scene.\n"
        "Each following image is a reference plant in this exact order:\n"
        f"{labels}\n\n"
        "Task: Count how many times EACH reference plant appears in the final garden scene.\n"
        "CRITICAL INSTRUCTIONS:\n"
        "- The plants in the garden scene may have been significantly altered by lighting, shading, rescaling, cropping, or slight shape warping during image generation.\n"
        "- Even if a plant's colors, lighting, or base are heavily blended into the soil/environment, you MUST still count it if its general structure is visible.\n"
        "Return ONLY valid JSON in this exact format:\n"
        '{"Plant 1": 0, "Plant 2": 0}'
    )

    request_contents = [counting_prompt, rendered_image]
    for plant_definition, reference_image in zip(plant_definitions, reference_images):
        request_contents.append(f"Reference image for {plant_definition['label']}")
        request_contents.append(reference_image)

    for model_name in COUNTING_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=request_contents,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT"],
                    response_mime_type="application/json",
                    temperature=0,
                ),
            )
            raw_counts = json.loads(response.text)
            normalized_counts = {}

            for plant in plant_definitions:
                label = plant["label"]
                value = raw_counts.get(label, 0)

                try:
                    normalized_counts[label] = int(value)
                except (TypeError, ValueError):
                    normalized_counts[label] = 0

            return normalized_counts
        except Exception as model_error:
            print(f"Counting model {model_name} failed: {model_error}")

    print("Plant counting error: no supported Gemini counting model succeeded.")
    return None

def create_garden_mockup(background_path, plants_data):
    """ইউজার থেকে পাওয়া স্পেসিফিক পজিশন অনুযায়ী এআই মকআপ তৈরি করে"""
    load_dotenv()
    client = genai.Client()
    plant_definitions = build_plant_definitions(plants_data)

    # ১. পিলো (Pillow) দিয়ে ব্যাকআপ লেআউট তৈরি করা
    try:
        bg_pil = Image.open(background_path).convert("RGBA")
        bg_width, bg_height = bg_pil.size
        final_pil = bg_pil.copy()
        
        plants_placed = 0
        for plant in plant_definitions:
            try:
                p_img = Image.open(plant['path']).convert("RGBA")
            except FileNotFoundError:
                continue
                
            orig_w, orig_h = p_img.size
            new_w = int(orig_w * plant['scale'])
            new_h = int(orig_h * plant['scale'])
            
            if new_w > 0 and new_h > 0:
                 p_img = p_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                 center_x = int(plant['x'] * bg_width)
                 center_y = int(plant['y'] * bg_height)
                 paste_x = center_x - (new_w // 2)
                 paste_y = center_y - (new_h // 2)
                 final_pil.paste(p_img, (paste_x, paste_y), p_img)
                 plants_placed += 1
                 
        if plants_placed > 0:
            final_out = final_pil.convert("RGB")
            final_out.save("exact_manual_render.jpg")
            print("Saved exactly-positioned layout to exact_manual_render.jpg\n")
    except Exception as e:
        print(f"Pillow precision mockup failed: {e}")

    # ২. এআই প্রম্পট এবং জেনারেশন লজিক
    try:
        background_img = Image.open(background_path)
        plant_images = [Image.open(plant["path"]) for plant in plant_definitions]
    except FileNotFoundError as e:
        print(f"Error finding image: {e}")
        return None

    positioning_info = "\n".join([
        f"{plant['label']}: Position ({plant['x']}, {plant['y']}) on canvas, Scale: {plant['scale']}x"
        for plant in plant_definitions
    ])

    prompt = (
            "You are an expert garden visualization AI. Your task is to create a realistic preview of how selected plants and flowers will look when placed in the user's garden photo. "
            
            "ABSOLUTE CRITICAL REQUIREMENTS: "
            "- You MUST place EXACTLY " + str(len(plant_definitions)) + " plant(s) in the final image. "
            "- EVERY single plant image provided must be placed and visible. Do NOT skip any plants. "
            "- Each plant MUST be placed at the EXACT specified position and scale. These are NOT suggestions - they are MANDATORY requirements. "
            "- Do NOT add extra copies of plants. Only place each plant image exactly once at its specified location. "
            
            "EXACT PLANT PLACEMENT INSTRUCTIONS (NON-NEGOTIABLE):\n" + positioning_info + "\n"
            "Canvas coordinate system: (0, 0) = top-left corner, (1, 1) = bottom-right corner, (0.5, 0.5) = center.\n"
            "Position values indicate the CENTER point where each plant should be placed.\n"
            "Scale values are multipliers for the plant's original size.\n"
            "Follow these positions EXACTLY as specified. "
            
            "Follow these rules carefully: "
            
            "1. BASE IMAGE PRESERVATION & ENHANCEMENT: Treat the first image as the main garden scene. Keep its layout, structures, and existing elements unchanged. "
            "You may enhance image quality (lighting balance, color clarity, sharpness) only if needed to improve realism. Do NOT alter the garden design. "
            
            "2. PLANT BACKGROUND REMOVAL & EXTRACTION: Remove any background, pots, walls, or other objects from the provided plant images. "
            "Extract ONLY the plant itself with clean edges, preserving transparency where the background was removed. "
            
            "3. PLANT POSITIONING: Place each plant at its exact specified position and scale: \n" + positioning_info + "\n"
            "Position (x,y) represents the center point of each plant on the canvas.\n"
            "Do NOT deviate from these specifications. Do NOT add extra plants. Do NOT remove or skip any plants. "
            
            "4. REALISTIC SCALE & PERSPECTIVE: Size each plant according to its scale value. "
            "Adjust depth and angle based on position (foreground, midground, background) to maintain natural perspective. "
            "Ensure each plant blends naturally into the scene while maintaining the specified positioning. "
            
            "5. LIGHTING, SHADOW & BLENDING: Match the lighting of the garden photo exactly. "
            "Add realistic shadows beneath each plant. Blend plant bases smoothly into soil, grass, or ground surfaces. "
            
            "6. FINAL VERIFICATION: Before returning, count and verify that:\n"
            "    - Exactly " + str(len(plant_definitions)) + " plant(s) are visible in the final image\n"
            "    - Each plant is at its specified position with its specified scale\n"
            "    - No plant backgrounds remain visible\n"
            "    - The image appears as a realistic photograph of the planted garden"
    )

    request_contents = [prompt, background_img] + plant_images
    
    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-image-preview',
            contents=request_contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9"
                )
            )
        )
        
        for part in response.parts:
            if part.inline_data:
                # PIL অবজেক্টে রূপান্তর
                output_image = part.as_image()
                
                # ভেরিফিকেশনের জন্য ফাইলে সেভ করা
                temp_filename = "temp_ai_render.jpg"
                output_image.save(temp_filename)

                # কাউন্টিং চেক
                plant_counts = estimate_plant_counts(client, temp_filename, plant_definitions)
                if plant_counts:
                    print("AI Plant Verification Results:")
                    print(json.dumps(plant_counts, indent=2))

                # জ্যাঙ্গোর জন্য ContentFile রিটার্ন করা
                buffer = io.BytesIO()
                output_image.save(buffer, format="JPEG")
                return ContentFile(buffer.getvalue(), name="ai_garden_render.jpg")

        print("The API responded, but no images were found in the output.")
        return None

    except Exception as e:
        print(f"API Error: {e}")
        return None
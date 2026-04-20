import io
import json
import os
import requests
from io import BytesIO
from django.core.files.base import ContentFile
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

# এআই কাউন্টিং মডেল লিস্ট
COUNTING_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

# --- HIGHLIGHT: FLEXIBLE IMAGE LOADER ---
# কেন: জ্যাঙ্গো ভিউ থেকে আসা Wikimedia URL সরাসরি Pillow দিয়ে ওপেন করা যায় না।
# এটি URL হলে ডাউনলোড করবে, লোকাল ফাইল হলে সরাসরি ওপেন করবে।
def open_image_flexible(path):
    if isinstance(path, Image.Image):
        return path
    path_str = str(path)
    if path_str.startswith(('http://', 'https://')):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(path_str, headers=headers, timeout=10)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
        except Exception as e:
            print(f"Failed to download image from URL {path_str}: {e}")
            raise FileNotFoundError(f"Could not load image from URL: {path_str}")
    else:
        return Image.open(path_str)

def build_plant_definitions(plants_data):
    if not plants_data: return []
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
    return [{"label": f"Plant {i+1}", "path": p, "x": 0.5, "y": 0.5, "scale": 1.0} for i, p in enumerate(plants_data)]

def estimate_plant_counts(client, rendered_image_obj, plant_definitions):
    try:
        # --- HIGHLIGHT: DIRECT OBJECT PASSING ---
        # কেন: ফাইল পাথ না পাঠিয়ে সরাসরি ইমেজ অবজেক্ট ব্যবহার করলে "File Not Found" এরর হয় না।
        reference_images = [open_image_flexible(plant["path"]) for plant in plant_definitions]
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
        "Return ONLY valid JSON in this exact format: {'Plant 1': 0, 'Plant 2': 0}"
    )

    request_contents = [counting_prompt, rendered_image_obj]
    for plant_def, ref_img in zip(plant_definitions, reference_images):
        request_contents.append(f"Reference image for {plant_def['label']}")
        request_contents.append(ref_img)

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
            return json.loads(response.text)
        except Exception: continue
    return None

def create_garden_mockup(background_path, plants_data):
    load_dotenv()
    client = genai.Client()
    plant_definitions = build_plant_definitions(plants_data)

    # -- Step 1: Pillow precision composite -----------
    try:
        # --- HIGHLIGHT: URL COMPATIBLE BACKGROUND ---
        bg_pil = open_image_flexible(background_path).convert("RGBA")
        bg_width, bg_height = bg_pil.size
        final_pil = bg_pil.copy()

        plants_placed = 0
        for plant in plant_definitions:
            try:
                # --- HIGHLIGHT: URL COMPATIBLE PLANT ---
                p_img = open_image_flexible(plant['path']).convert("RGBA")
                orig_w, orig_h = p_img.size
                new_w = int(orig_w * plant['scale'])
                new_h = int(orig_h * plant['scale'])

                if new_w > 0 and new_h > 0:
                    p_img = p_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    center_x = int(plant['x'] * bg_width)
                    center_y = int(plant['y'] * bg_height)
                    paste_x = center_x - (new_w // 2)
                    paste_y = center_y - (new_h // 2)

                    # Clamp to canvas bounds
                    paste_x = max(0, min(paste_x, bg_width - new_w))
                    paste_y = max(0, min(paste_y, bg_height - new_h))

                    final_pil.paste(p_img, (paste_x, paste_y), p_img)
                    plants_placed += 1
            except: continue

        if plants_placed == 0: return None
        
        # জেনারেট করা কম্পোজিটটি মেমোরিতে রাখা
        composited_img = final_pil.convert("RGB")
        
    except Exception as e:
        print(f"Pillow precision mockup failed: {e}")
        return None

    # -- Step 2: Gemini enhancement only --------
    plant_list_text = "\n".join(
        [f"- A plant located at approximately X:{int(p['x']*100)}%, Y:{int(p['y']*100)}%" for p in plant_definitions]
    )

    enhancement_prompt = (
        "You are an expert digital artist and photo retoucher. "
        "The provided input image is a rough composite where plants have been artificially pasted onto a background. "
        "Your task is to generate a completely NEW, photorealistic image based on this draft. "
        f"\n\nCRUCIAL INSTRUCTION: There are exactly {len(plant_definitions)} newly pasted plants in this image. "
        f"They are located at:\n{plant_list_text}\n"
        "You MUST process, shade, and blend EVERY SINGLE ONE of these plants. "
        "\n\n1. SEAMLESS INTEGRATION: Blend bases naturally. "
        "2. LIGHTING & SHADOWS: Add realistic drop shadows. "
        "3. HARMONIZATION: Match color temperature and contrast. "
    )

    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-image-preview',
            contents=[enhancement_prompt, composited_img],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"])
        )

        for part in response.parts:
            if part.inline_data:
                # --- HIGHLIGHT: MEMORY SAFE OUTPUT ---
                # কেন: ফাইল সেভ না করে সরাসরি বাইট থেকে ইমেজ তৈরি করা হচ্ছে।
                output_image = Image.open(io.BytesIO(part.inline_data.data))

                # ভেরিফিকেশন (কাউন্টিং)
                plant_counts = estimate_plant_counts(client, output_image, plant_definitions)
                if plant_counts:
                    print("AI Verification:", json.dumps(plant_counts, indent=2))

                # --- HIGHLIGHT: DJANGO CONTENTFILE RETURN ---
                # কেন: জ্যাঙ্গো ভিউ এই ফরম্যাটটিই ডাটাবেসে সেভ করতে পারে।
                buffer = io.BytesIO()
                output_image.save(buffer, format="JPEG")
                return ContentFile(buffer.getvalue(), name="ai_garden_render.jpg")

    except Exception as e:
        print(f"API Error during Gemini enhancement: {e}")
        return None
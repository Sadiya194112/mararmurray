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

COUNTING_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


def build_plant_definitions(plants_data):
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


def normalize_scale(plant_orig_width, bg_width, target_fraction):
    """
    Compute a scale multiplier so the plant occupies `target_fraction` of the
    background width.  E.g. target_fraction=0.15 -> plant fills 15% of bg.
    """
    return (target_fraction * bg_width) / plant_orig_width


def suggest_plant_placements(background_path, plant_paths):
    """
    Print AI-style placement suggestions for each plant based on the background
    dimensions and perspective-correct depth zones.
    """
    try:
        bg = open_image_flexible(background_path)
        bw, bh = bg.size
    except FileNotFoundError:
        print(f"suggest_plant_placements: background not found: {background_path}")
        return []

    zones = [
        ("Foreground left",    0.20, 0.82, 0.15),
        ("Foreground right",   0.80, 0.82, 0.15),
        ("Foreground center",  0.50, 0.88, 0.17),
        ("Midground left",     0.25, 0.62, 0.11),
        ("Midground right",    0.75, 0.62, 0.11),
        ("Midground center",   0.50, 0.60, 0.12),
        ("Background left",    0.15, 0.42, 0.06),
        ("Background right",   0.85, 0.42, 0.06),
        ("Background center",  0.50, 0.40, 0.06),
    ]

    suggestions = []
    print(f"\n{'=' * 60}")
    print(f"  AI PLACEMENT SUGGESTIONS  (bg={bw}x{bh} px)")
    print(f"{'=' * 60}")

    for plant_path in plant_paths:
        try:
            pi = open_image_flexible(plant_path)
            pw, ph = pi.size
            has_alpha = pi.mode in ("RGBA", "LA", "PA")
        except FileNotFoundError:
            continue

        print(f"\n  Plant: {plant_path}  ({pw}x{ph} px, alpha={has_alpha})")
        if not has_alpha:
            print("  [!] No alpha channel detected - background removal recommended (rembg).")
        print(f"  {'Zone':<25} {'x':>5}  {'y':>5}  {'scale':>6}  {'px size'}")
        print(f"  {'-' * 57}")

        plant_suggestions = []
        for zone_name, sx, sy, tf in zones:
            s = normalize_scale(pw, bw, tf)
            nw = int(pw * s)
            nh = int(ph * s)
            print(f"  {zone_name:<25} {sx:>5.2f}  {sy:>5.2f}  {s:>6.3f}  {nw}x{nh} px")
            plant_suggestions.append({"zone": zone_name, "x": sx, "y": sy, "scale": round(s, 4)})

        suggestions.append({"path": plant_path, "zones": plant_suggestions})

    print(f"{'=' * 60}\n")
    return suggestions


def estimate_plant_counts(client, rendered_image_path, plant_definitions):
    try:
        rendered_image = open_image_flexible(rendered_image_path)
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


def _load_plant_rgba(path):
    """
    Load a plant image as RGBA.
    """
    raw = open_image_flexible(path)
    result = raw.convert("RGBA")
    return result


def create_garden_mockup(background_path, plants_data):
    load_dotenv()
    client = genai.Client()
    plant_definitions = build_plant_definitions(plants_data)

    # -- Step 1: Pillow precision composite (reliable coordinates) -----------
    try:
        bg_pil = open_image_flexible(background_path).convert("RGBA")
        bg_width, bg_height = bg_pil.size
        final_pil = bg_pil.copy()

        plants_placed = 0
        for plant in plant_definitions:
            try:
                p_img = _load_plant_rgba(plant['path'])
            except FileNotFoundError:
                print(f"  [SKIP] Plant image not found: {plant['path']}")
                continue

            orig_w, orig_h = p_img.size
            new_w = int(orig_w * plant['scale'])
            new_h = int(orig_h * plant['scale'])

            if new_w > 0 and new_h > 0:
                p_img = p_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                center_x = int(plant['x'] * bg_width)
                center_y = int(plant['y'] * bg_height)
                paste_x  = center_x - (new_w // 2)
                paste_y  = center_y - (new_h // 2)

                # Clamp to canvas bounds so plants never go out-of-bounds
                paste_x = max(0, min(paste_x, bg_width  - new_w))
                paste_y = max(0, min(paste_y, bg_height - new_h))

                final_pil.paste(p_img, (paste_x, paste_y), p_img)
                plants_placed += 1
                print(f"  Placed {plant['label']} at center=({center_x},{center_y}), "
                      f"size={new_w}x{new_h}px, scale={plant['scale']:.3f}")

        if plants_placed > 0:
            final_out = final_pil.convert("RGB")
            final_out.save("exact_manual_render.jpg")
            print("Saved exactly-positioned layout -> exact_manual_render.jpg\n")
        else:
            print("[WARNING] No plants were successfully placed in the manual render.")
            return

    except Exception as e:
        print(f"Pillow precision mockup failed: {e}")
        return

    # -- Step 2: Gemini enhancement only (lighting, shadows, blending) --------
    # We send the already-composited Pillow output.  Gemini doesn't re-position
    # plants - it only enhances the realism of the existing composite.
    try:
        composited_img = Image.open("exact_manual_render.jpg")
    except FileNotFoundError as e:
        print(f"Cannot load composited image for Gemini enhancement: {e}")
        return

    plant_list_text = "\n".join(
        [f"- A plant located at approximately X:{int(p['x']*100)}%, Y:{int(p['y']*100)}%" for p in plant_definitions]
    )

    enhancement_prompt = (
        "You are an expert digital artist and photo retoucher. "
        "The provided input image is a rough composite where plants have been artificially pasted onto a background. "
        "Your task is to generate a completely NEW, photorealistic image based on this draft. "
        "Do not simply return the input image; you MUST generate a newly synthesized image with enhanced realism. "
        f"\n\nCRUCIAL INSTRUCTION: There are exactly {len(plant_definitions)} newly pasted plants in this image that require processing. "
        f"They are located at:\n{plant_list_text}\n"
        "You MUST process, shade, and blend EVERY SINGLE ONE of these plants. Do not skip or leave any of them unmodified. "
        "\n\nCRITICAL ENHANCEMENTS: "
        "\n1. SEAMLESS INTEGRATION: Keep the plants in their current locations and sizes, but completely re-render "
        "them so they look 100% natural. Blend their bases seamlessly into the soil, grass, or path."
        "\n2. LIGHTING & SHADOWS: Match the global lighting direction of the background. Add realistic drop shadows, "
        "contact shadows, and ambient occlusion beneath and around EVERY pasted plant. "
        "\n3. HARMONIZATION: Adjust the color temperature, saturation, and contrast of ALL pasted plants to match the "
        "environment perfectly. Remove any artificial halos or sharp cutout edges. "
        "\n4. PHOTOREALISM: Ensure the final output looks like a single, unified photograph taken with a high-quality camera."
    )

    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-image-preview',
            contents=[enhancement_prompt, composited_img],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            )
        )

        count = 0
        final_django_file = None
        for part in response.parts:
            if part.inline_data:
                output_image = part.as_image()
                output_filename = f"final_garden_render_V2{count}.jpg"
                output_image.save(output_filename)
                print(f"Saved enhanced render -> {output_filename}")

                plant_counts = estimate_plant_counts(client, output_filename, plant_definitions)
                if plant_counts:
                    print(json.dumps(plant_counts, indent=2))

                count += 1
                
                if count == 1:
                    buffer = io.BytesIO()
                    output_image.save(buffer, format="JPEG")
                    final_django_file = ContentFile(buffer.getvalue(), name="ai_garden_render.jpg")

        if count == 0:
            print("The API responded, but no images were found in the output.")
            
        return final_django_file

    except Exception as e:
        print(f"API Error during Gemini enhancement: {e}")
        return None

if __name__ == "__main__":

    core_background = "background 2.jpg"

    # -- Optional: print AI placement suggestions before running -------------
    # Uncomment to see which zones look best for your background dimensions:
    # suggest_plant_placements(core_background, ["Plant 3.png", "Plant 4.png"])

    # -- Plant definitions ---------------------------------------------------
    # Scale is now calibrated so the plant fills a reasonable fraction of the
    # background (15% of width = foreground, 11% = midground, 6% = background).
    #
    # Background is 5315x3541 px. Current normalized scales:
    #   0.83 -> plant fills ~15% of bg width (foreground presence)
    #   0.52 -> plant fills ~10% of bg width (natural midground)
    #
    # Tip: use suggest_plant_placements() to explore all zone options.

    new_plants = [
        {
            "label": "Plant 3",
            "path": "Plant 3.png",
            "x": 0.35,   # left-center
            "y": 0.78,   # foreground
            "scale": 0.83,  # ~15% of bg width -> natural foreground size
        },
        {
            "label": "Plant 4",
            "path": "Plant 4.png",
            "x": 0.70,   # right area
            "y": 0.62,   # midground
            "scale": 0.52,  # ~10% of bg width -> natural midground size
        },
    ]

    create_garden_mockup(core_background, new_plants)
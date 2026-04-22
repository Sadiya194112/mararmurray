import io
import json
from io import BytesIO

import requests
from django.core.files.base import ContentFile
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

try:
    from rembg import remove as rembg_remove

    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    print(
        "[WARNING] rembg not installed. Run: pip install rembg  — plant backgrounds will NOT be removed before compositing."
    )


def open_image_flexible(path):
    if isinstance(path, Image.Image):
        return path
    path_str = str(path)
    if path_str.startswith(("http://", "https://")):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
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
        ("Foreground left", 0.20, 0.82, 0.15),
        ("Foreground right", 0.80, 0.82, 0.15),
        ("Foreground center", 0.50, 0.88, 0.17),
        ("Midground left", 0.25, 0.62, 0.11),
        ("Midground right", 0.75, 0.62, 0.11),
        ("Midground center", 0.50, 0.60, 0.12),
        ("Background left", 0.15, 0.42, 0.06),
        ("Background right", 0.85, 0.42, 0.06),
        ("Background center", 0.50, 0.40, 0.06),
    ]

    suggestions = []
    print(f"\n{'=' * 60}")
    print(f"  AI PLACEMENT SUGGESTIONS  (bg={bw}x{bh} px)")
    print(f"{'=' * 60}")

    for plant_path in plant_paths:
        try:
            pi = open_image_flexible(plant_path)
            pw, ph = pi.size
            # has_alpha = pi.mode in ("RGBA", "LA", "PA")
        except FileNotFoundError:
            continue

        print(f"\n  Plant: {plant_path}  ({pw}x{ph} px")

        plant_suggestions = []
        for zone_name, sx, sy, tf in zones:
            s = normalize_scale(pw, bw, tf)
            nw = int(pw * s)
            nh = int(ph * s)
            print(f"  {zone_name:<25} {sx:>5.2f}  {sy:>5.2f}  {s:>6.3f}  {nw}x{nh} px")
            plant_suggestions.append(
                {"zone": zone_name, "x": sx, "y": sy, "scale": round(s, 4)}
            )

        suggestions.append({"path": plant_path, "zones": plant_suggestions})

    print(f"{'=' * 60}\n")
    return suggestions


def estimate_plant_counts(client, rendered_image_path, plant_definitions):
    try:
        rendered_image = open_image_flexible(rendered_image_path)
        reference_images = [
            open_image_flexible(plant["path"]) for plant in plant_definitions
        ]
    except FileNotFoundError as e:
        print(f"Error finding image for count analysis: {e}")
        return None

    labels = ", ".join(plant["label"] for plant in plant_definitions)
    counting_prompt = (
        "You are an expert image analyst counting elements in a modified photo.\n"
        "The first image is the final generated garden scene.\n"
        f"Each following image is a reference plant in this exact order: {labels}\n\n"
        "Count how many times EACH reference plant appears in the final garden scene.\n"
        "Return ONLY valid JSON: " + '{"Plant 1": 0, "Plant 2": 0}'
    )

    request_contents = [counting_prompt, rendered_image]
    for pd, ri in zip(plant_definitions, reference_images):
        request_contents += [f"Reference image for {pd['label']}", ri]

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
            raw = json.loads(response.text)
            return {p["label"]: int(raw.get(p["label"], 0)) for p in plant_definitions}
        except Exception as err:
            print(f"Counting model {model_name} failed: {err}")
    return None


def _draw_position_markers(bg_rgb, plant_definitions):
    """Draw coloured circle + label on background for each plant — no rembg needed."""
    from PIL import ImageDraw

    marked = bg_rgb.copy()
    draw = ImageDraw.Draw(marked)
    bw, bh = marked.size
    colors = [(255, 60, 60), (60, 60, 255), (60, 200, 60), (255, 200, 0)]
    for i, p in enumerate(plant_definitions):
        cx, cy = int(p["x"] * bw), int(p["y"] * bh)
        r = max(30, int(min(bw, bh) * 0.018))
        col = colors[i % len(colors)]
        draw.ellipse(
            (cx - r, cy - r, cx + r, cy + r), outline=col, width=max(5, r // 3)
        )
        # Cross-hair so the exact base point is clear
        draw.line((cx - r, cy, cx + r, cy), fill=col, width=3)
        draw.line((cx, cy - r, cx, cy + r), fill=col, width=3)
        draw.text((cx + r + 10, cy - r // 2), p["label"], fill=col)
    return marked


def create_garden_mockup(background_path, plants_data):
    """
    Reference-based painting pipeline:

    Instead of extracting cut-outs (which fails on macro flower photos),
    we send Gemini:
      - The clean background with position markers (WHERE to place plants)
      - Each original plant photo unmodified (WHAT the plant looks like)

    Gemini then paints each plant naturally into the marked location,
    reconstructing stems, foliage, and ground anchoring from the reference.
    """
    load_dotenv()
    client = genai.Client()
    plant_definitions = build_plant_definitions(plants_data)

    # 1. Load background
    final_django_file = None

    try:
        bg_rgb = open_image_flexible(background_path).convert("RGB")
        bg_w, bg_h = bg_rgb.size
        print(f"Background: {bg_w}x{bg_h} px")

    except FileNotFoundError:
        print(f"[ERROR] Background not found: {background_path}")
        return

    # 2. Position-marker image (saved as the manual render for reference)
    marker_img = _draw_position_markers(bg_rgb, plant_definitions)
    marker_img.convert("RGB").save("exact_manual_render.jpg", format="JPEG", quality=95)
    print("Saved position-marker layout -> exact_manual_render.jpg")

    # 3. Load each plant as an unmodified reference photo
    plant_refs = []
    for p in plant_definitions:
        try:
            ref = open_image_flexible(p["path"]).convert("RGB")
            # Shrink very large images to keep API payload reasonable
            if max(ref.size) > 900:
                ratio = 900 / max(ref.size)
                ref = ref.resize(
                    (int(ref.width * ratio), int(ref.height * ratio)),
                    Image.Resampling.LANCZOS,
                )
            plant_refs.append((p, ref))
            print(f"  Reference '{p['label']}': {ref.size}")
        except FileNotFoundError:
            print(f"  [SKIP] Not found: {p['path']}")

    if not plant_refs:
        print("[ERROR] No plant references loaded.")
        return

    # 4. Build prompt
    color_names = ["red", "blue", "green", "yellow"]

    ref_lines = "".join(
        "  Image %d: reference photo of %s (place at the %s marker).\n"
        % (i + 2, p["label"], color_names[i % len(color_names)])
        for i, (p, _) in enumerate(plant_refs)
    )

    placement_lines = "\n".join(
        "- %s (%s circle): plant BASE at X=%d%%, Y=%d%% of image. Use Image %d as reference."
        % (
            p["label"],
            color_names[i % len(color_names)],
            int(p["x"] * 100),
            int(p["y"] * 100),
            i + 2,
        )
        for i, (p, _) in enumerate(plant_refs)
    )

    prompt = (
        "You are a professional garden visualisation artist.\n\n"
        "INPUTS:\n"
        "  Image 1: real garden photo with coloured circle+crosshair markers "
        "showing WHERE new plants must be placed.\n" + ref_lines + "\nTASK:\n"
        "Produce a photorealistic version of the garden with each marked plant "
        "painted in naturally. Erase the marker circles from the output.\n\n"
        "PLACEMENT:\n" + placement_lines + "\n\nRULES (every rule is mandatory):\n"
        "1. WHOLE PLANT: Paint the COMPLETE plant from soil to flower tip - "
        "roots/base in ground, full stem, all leaves, flowers on top. "
        "A flower head with no stem is a failure.\n"
        "2. SCALE: Y>70% = foreground = larger plant. Y<55% = background = smaller.\n"
        "3. ROOTED: Base blends into soil/gravel/mulch. Plant looks like it has "
        "always grown there - no floating, no pasting.\n"
        "4. LIGHTING: Overcast diffuse light matching the scene. Soft ground shadow.\n"
        "5. BACKGROUND UNCHANGED: Every rock, path, bridge, fence, and existing "
        "plant must be pixel-identical to Image 1.\n"
        "6. PHOTOREALISTIC JPEG output only."
    )

    contents = [prompt, marker_img] + [ref for _, ref in plant_refs]
    print(
        f"\nSending to Gemini: 1 marker image + {len(plant_refs)} plant reference(s)..."
    )

    # 5. Call Gemini — try models in order until one works
    IMAGE_GEN_MODELS = [
        "nano-banana-pro-preview",
        "gemini-3.1-flash-image-preview",
        "gemini-2.5-flash-image",
        "gemini-3-pro-image-preview",
    ]

    response = None
    used_model = None
    for model_name in IMAGE_GEN_MODELS:
        try:
            print(f"  Trying model: {model_name} ...")
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )
            used_model = model_name
            print(f"  Success with: {model_name}")
            break
        except Exception as model_err:
            print(f"  {model_name} unavailable: {model_err}")

    try:
        if response is None:
            print("[ERROR] No image-generation model available on this account.")
            print(
                'Run: python -c "from google import genai; c=genai.Client(); [print(m.name) for m in c.models.list()]" to see available models.'
            )
            return None

        count = 0
        generated_file = None
        for part in response.parts:
            if part.inline_data:
                raw_bytes = part.inline_data.data
                out_img = Image.open(io.BytesIO(raw_bytes))
                out_name = f"final_garden_render_V2{count}.jpg"
                out_img.convert("RGB").save(out_name, format="JPEG", quality=95)
                print(f"Saved -> {out_name}")
                counts = estimate_plant_counts(client, out_name, plant_definitions)
                if counts:
                    print(json.dumps(counts, indent=2))
                if count == 0:  # Return the first generated image
                    generated_file = ContentFile(raw_bytes, name="garden_ai.jpg")
                count += 1
            elif hasattr(part, "text") and part.text:
                print(f"  Gemini text: {part.text[:300]}")

        if count == 0:
            print(
                "[WARNING] Gemini returned no image even though the call succeeded.\n"
                f"  Model used: {used_model}\n"
                "  The marker layout is saved as exact_manual_render.jpg."
            )
            return None

        return generated_file

    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Gemini API error: {e}")
        return None


if __name__ == "__main__":
    core_background = "background 3.jpg"

    new_plants = [
        {
            "label": "Plant 3",
            "path": "Plant 3.png",
            "x": 0.35,
            "y": 0.78,
            "scale": 0.83,
        },
        {
            "label": "Plant 4",
            "path": "Plant 4.png",
            "x": 0.70,
            "y": 0.62,
            "scale": 0.52,
        },
    ]

    create_garden_mockup(core_background, new_plants)

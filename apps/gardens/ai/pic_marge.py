from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image


def create_garden_mockup(background_path, plants_data):
    load_dotenv()
    client = genai.Client()
    try:
        background_img = Image.open(background_path)

        if isinstance(plants_data[0], dict):
            plant_images = [Image.open(plant["path"]) for plant in plants_data]
            plant_positions = plants_data
        else:
            plant_images = [Image.open(p) for p in plants_data]
            plant_positions = [
                {"path": p, "x": 0.5, "y": 0.5, "scale": 1.0} for p in plants_data
            ]
    except FileNotFoundError as e:
        print(f"Error finding image: {e}")
        return

    positioning_info = "\n".join(
        [
            f"Plant {i + 1}: Position ({p['x']}, {p['y']}) on canvas, Scale: {p['scale']}x"
            for i, p in enumerate(plant_positions)
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

        count = 0
        for part in response.parts:
            if part.inline_data:
                output_image = part.as_image()
                output_filename = f"final_garden_render_V2{count}.jpg"
                output_image.save(output_filename)
                print(f"Success! Your mockup has been saved as: {output_filename}")
                count += 1

        if count == 0:
            print("The API responded, but no images were found in the output.")

    except Exception as e:
        print(f"API Error: {e}")


if __name__ == "__main__":
    core_background = "garden.jpg"

    new_plants = [
        {"path": "flower - 1.jpg", "x": 0.25, "y": 0.6, "scale": 0.8},
        {"path": "flower - 2.jpg", "x": 0.7, "y": 0.4, "scale": 1.1},
    ]

    create_garden_mockup(core_background, new_plants)

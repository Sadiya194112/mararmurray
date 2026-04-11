import os
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

def create_garden_mockup(background_path, plant_paths):
    load_dotenv()
    client = genai.Client()
    try:
        background_img = Image.open(background_path)
        plant_images = [Image.open(p) for p in plant_paths]
    except FileNotFoundError as e:
        print(f"Error finding image: {e}")
        return

    prompt = (
            "You are an expert garden visualization AI. Your task is to create a realistic preview of how selected plants and flowers will look when placed in the user’s garden photo. "
            
            "Follow these rules carefully: "
            
            "1. BASE IMAGE PRESERVATION & ENHANCEMENT: Treat the first image as the main garden scene. Keep its layout, structures, and existing elements unchanged. "
            "You may slightly enhance the image quality (lighting balance, color clarity, sharpness) only if needed to improve realism, but do not alter the actual design or content of the garden. "
            
            "2. NATURAL PLANT PLACEMENT: Identify appropriate empty or underutilized areas such as soil beds, lawn edges, corners, or pathways. "
            "Place the new plants in a way that feels natural and aesthetically pleasing, as if they were actually planted there by a gardener. Avoid overcrowding. "
            
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
            model='gemini-3.1-flash-image-preview',
            contents=request_contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9"
                )
            )
        )
        
        count = 0
        for part in response.parts:
            if part.inline_data:

                output_image = part.as_image()
                output_filename = f"final_garden_render_{count}.jpg"
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
        "flower - 1.jpg", 
        "flower - 2.jpg"
    ]
    
    create_garden_mockup(core_background, new_plants)
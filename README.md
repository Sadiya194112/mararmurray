<div align="center">
  <h1>🌸 Florle</h1>
  <p><b>Your Personal AI-Powered Outdoor Flower Garden Architect</b></p>
</div>

---

## 📖 Overview
**Florle** is an intelligent, automated platform designed to help users envision, design, and maintain stunning outdoor flower gardens. By combining computer vision, generative AI, and real-time botanical data, Florle takes the guesswork out of gardening. Simply upload a picture of your yard or an empty garden space, and let AI transform it into a perfectly scaled, beautifully composed blooming paradise.

## ✨ Key Features
- 🖼️ **AI Image Quality Analysis:** Evaluates the quality and suitability of the uploaded garden photo before the design process begins.
- 🪴 **Smart Planting System:** Digitally plant multiple flowers in precise, user-chosen locations across the garden canvas.
- 🪄 **Gemini AI Compositing:** Magically blends chosen plants into your garden picture with perfect scaling, realistic lighting, and accurate positioning using **Google Gemini AI**.
- 🌱 **Automated Botanical Database:** Automatically fetches and syncs comprehensive plant data in the background using the **Perenual API** and **Celery**.
- 📅 **Smart Care Scheduling:** Once planted, the AI generates a customized timeline for when to plant and when to water, accompanied by intelligent reminders.

## 🛠️ Tech Stack
- **Backend Framework:** Django, Django REST Framework, Python 3.12
- **AI & Vision:** Google Gemini AI, OpenCV, Rembg
- **Background Processing:** Celery, Celery Beat & Redis (for asynchronous Perenual API data harvesting)
- **Database:** PostgreSQL
- **Containerization & Deployment:** Docker, Docker Compose, Nginx, Uvicorn
- **Dependency Management:** `uv`

## ⚙️ How It Works
1. **Upload:** Provide an image of your empty or existing garden space.
2. **Analyze:** The AI system checks the image quality to ensure an optimal composition canvas.
3. **Design:** Select your favorite plants and indicate exactly where you'd like them placed.
4. **Compose:** Gemini AI takes over, flawlessly placing, scaling, and blending the plants into your original photo.
5. **Maintain:** Receive an AI-generated, personalized schedule for planting and watering to keep your garden thriving.

## 🚀 Quick Commands
To fetch new plant data into the database using background workers:

```bash
# Start background plant harvesting
uv run manage.py start_harvesting

# Harvest 10 plants every hour for 2 days
uv run manage.py start_harvesting --days=2 --rate=10
```
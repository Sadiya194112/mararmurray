# ১. পাইথন ইমেজ নির্বাচন
FROM python:3.12-slim

# ২. ওয়ার্কিং ডিরেক্টরি তৈরি
WORKDIR /app

# ৩. এনভায়রনমেন্ট ভেরিয়েবল সেট করা
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# uv এর ভার্চুয়াল এনভায়রনমেন্ট সরাসরি ব্যবহারের জন্য পাথ সেট করা
ENV PATH="/app/.venv/bin:$PATH"

# ৪. সিস্টেম ডিপেন্ডেন্সি ইনস্টল
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libpq-dev \
    netcat-openbsd \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# ৫. uv ইনস্টল করা
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# ৬. ডিপেন্ডেন্সি ফাইল কপি (pyproject.toml এবং uv.lock)
COPY pyproject.toml uv.lock ./

# ৭. ডিপেন্ডেন্সি ইনস্টল করা (ভার্চুয়াল এনভায়রনমেন্ট তৈরি সহ)
RUN uv sync --frozen --no-cache

# ৮. প্রোজেক্ট ফাইল কপি করা
COPY . .

# ৯. পোর্ট এক্সপোজ করা
EXPOSE 8005

# ১০. প্রোডাকশন সেটিংস
ENV DJANGO_SETTINGS_MODULE=core.settings
ENV DEBUG=False

# ১১. রান কমান্ড (সরাসরি python -m uvicorn ব্যবহার করা হচ্ছে যা .venv থেকে আসবে)
CMD ["python", "-m", "uvicorn", "core.asgi:application", "--host", "0.0.0.0", "--port", "8005", "--workers", "4", "--log-level", "info"]
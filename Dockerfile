FROM python:3.11.13-slim-bullseye

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libmariadb-dev \
    netcat \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .



EXPOSE 8005

#
CMD ["python", "-m", "uvicorn", "core.asgi:application", "--host", "0.0.0.0", "--port", "8005"]

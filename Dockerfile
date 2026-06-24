# ===========================================================
# Dockerfile - Auto Data Analyzer
# EN: Single-stage image running FastAPI (backend) which also
#     serves the static frontend (frontend/index.html).
# AR: صورة Docker واحدة تشغّل FastAPI، وتعرض أيضاً الواجهة
#     الأمامية الثابتة (frontend/index.html).
# ===========================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ----- System dependencies (minimal, kept slim) -----
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ----- Install Python dependencies first (better layer caching) -----
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# ----- Copy application code -----
COPY backend /app/backend
COPY frontend /app/frontend

WORKDIR /app/backend

EXPOSE 8000

# ----- Run the FastAPI app with Uvicorn -----
# EN: Render (and most free hosts) inject a $PORT env var at runtime and
#     expect the app to bind to it instead of a hardcoded port. We use the
#     shell form so $PORT is expanded; default to 8000 for local `docker run`.
# AR: Render (وأغلب الاستضافات المجانية) بيحدد متغير بيئة $PORT وقت التشغيل
#     ولازم التطبيق يشتغل عليه بدل بورت ثابت. بنستخدم shell form عشان
#     يتم تفسير $PORT، مع قيمة افتراضية 8000 لو شغلت الكونتينر محلياً.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

"""
main.py
--------
EN: FastAPI application entrypoint. Wires up CORS, routers, and serves the
    simple static frontend (index.html) if present.
AR: نقطة دخول تطبيق FastAPI. يضبط CORS والـ Routers، ويعرض الواجهة الأمامية
    البسيطة (index.html) إن وُجدت.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

from app.routers import analysis

app = FastAPI(
    title="Auto Data Analyzer API",
    description="نظام تحليل بيانات تلقائي يختار الرسوم البيانية المناسبة بدون تدخل بشري",
    version="1.0.0",
)

# ---------- CORS ----------
# EN: Allow all origins for simplicity (tighten this in production!)
# AR: السماح لجميع المصادر للتبسيط (يجب تقييدها في بيئة الإنتاج!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Routers ----------
app.include_router(analysis.router)

# ---------- Static frontend (optional) ----------
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_frontend():
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Auto Data Analyzer API is running. لا يوجد ملف index.html"}

    @app.get("/dashboard/{session_id}")
    async def serve_dashboard(session_id: str):
        """
        EN: Serves the dashboard HTML page. The page itself reads session_id
            from the URL (via JavaScript) and fetches /api/session/{id}.
            This is the link sent by the Telegram bot to the user.
        AR: يعرض صفحة الداشبورد. الصفحة نفسها تقرأ session_id من الرابط
            (عبر JavaScript) وتجلب البيانات من /api/session/{id}.
            هذا هو الرابط الذي يرسله بوت تليجرام للمستخدم.
        """
        dashboard_path = os.path.join(FRONTEND_DIR, "dashboard.html")
        if os.path.exists(dashboard_path):
            return FileResponse(dashboard_path)
        return {"message": "لا يوجد ملف dashboard.html"}

else:
    @app.get("/")
    async def root():
        return {"message": "Auto Data Analyzer API is running 🚀"}

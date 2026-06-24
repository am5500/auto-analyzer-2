"""
analysis.py
------------
EN: API routes related to uploading a file and getting back chart suggestions.
    Also exposes a GET-by-session endpoint so a dashboard page (or a Telegram
    bot) can fetch a previously computed analysis by its session_id.
AR: نقاط النهاية (Endpoints) المسؤولة عن رفع الملف والحصول على الرسوم المقترحة.
    كما توفر نقطة GET لاسترجاع تحليل سابق عبر session_id، تُستخدم من صفحة
    الـ Dashboard أو من بوت تليجرام.
"""

from __future__ import annotations

import time
import uuid
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.chart_builder import render_chart_to_json
from app.services.chart_selector import suggest_charts
from app.services.file_loader import UnsupportedFileTypeError, load_dataframe

router = APIRouter(prefix="/api", tags=["analysis"])

# Simple in-memory store of completed analysis results, keyed by session id.
# EN: For a production system with multiple server instances, replace this
#     with Redis or a database — in-memory storage is per-process and is
#     lost on restart, and won't be shared across instances/workers.
# AR: للإنتاج الحقيقي مع أكثر من Instance، يُفضّل استبدال هذا بـ Redis أو
#     قاعدة بيانات — التخزين بالذاكرة مرتبط بالعملية الواحدة ويُفقد عند
#     إعادة التشغيل، ولا يُشارك بين عدة Instances/Workers.
_RESULTS_STORE: dict[str, "AnalyzeResponseOut"] = {}

# How long a session's result stays available (in seconds). 24 hours here.
SESSION_TTL_SECONDS = 24 * 60 * 60
_SESSION_TIMESTAMPS: dict[str, float] = {}

MAX_FILE_SIZE_MB = 20


class ChartResultOut(BaseModel):
    chart_type: str
    title: str
    explanation_ar: str
    explanation_en: str
    figure_json: str


class AnalyzeResponseOut(BaseModel):
    session_id: str
    n_rows: int
    n_columns: int
    columns: List[str]
    charts: List[ChartResultOut]


def _cleanup_expired_sessions() -> None:
    """EN: Drop sessions older than TTL to avoid unbounded memory growth.
    AR: حذف الجلسات الأقدم من TTL لتجنب تضخم الذاكرة بلا حدود."""
    now = time.time()
    expired = [sid for sid, ts in _SESSION_TIMESTAMPS.items() if now - ts > SESSION_TTL_SECONDS]
    for sid in expired:
        _RESULTS_STORE.pop(sid, None)
        _SESSION_TIMESTAMPS.pop(sid, None)


@router.post("/analyze", response_model=AnalyzeResponseOut)
async def analyze_file(file: UploadFile = File(...)) -> AnalyzeResponseOut:
    """
    EN: Main endpoint — upload a CSV/Excel file, get back 3-5 chart suggestions
        with explanations, fully automatically (no manual axis selection).
        The result is also stored under a session_id for later retrieval
        (used by the dashboard page and the Telegram bot).
    AR: نقطة النهاية الأساسية — رفع ملف CSV/Excel والحصول على 3-5 رسوم مقترحة
        مع تفسير نصي، بشكل تلقائي بالكامل. تُخزَّن النتيجة أيضاً تحت
        session_id لاسترجاعها لاحقاً (تُستخدم من صفحة الداشبورد وبوت تليجرام).
    """
    _cleanup_expired_sessions()

    file_bytes = await file.read()

    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"حجم الملف كبير جداً ({size_mb:.1f}MB). الحد الأقصى {MAX_FILE_SIZE_MB}MB",
        )

    try:
        df = load_dataframe(file.filename, file_bytes)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"فشل في قراءة الملف: {exc}") from exc

    suggestions = suggest_charts(df, max_suggestions=5)

    if not suggestions:
        raise HTTPException(
            status_code=422,
            detail="لم نتمكن من استخراج رسوم بيانية مناسبة من هذا الملف. تأكد من وجود أعمدة رقمية أو تاريخية.",
        )

    charts_out: List[ChartResultOut] = []
    for suggestion in suggestions:
        figure_json = render_chart_to_json(df, suggestion)
        if figure_json is None:
            continue  # skip charts that failed to render
        charts_out.append(
            ChartResultOut(
                chart_type=suggestion.chart_type,
                title=suggestion.title,
                explanation_ar=suggestion.explanation_ar,
                explanation_en=suggestion.explanation_en,
                figure_json=figure_json,
            )
        )

    if not charts_out:
        raise HTTPException(status_code=422, detail="تعذّر بناء أي رسم بياني من هذه البيانات")

    session_id = str(uuid.uuid4())
    result = AnalyzeResponseOut(
        session_id=session_id,
        n_rows=df.shape[0],
        n_columns=df.shape[1],
        columns=list(df.columns),
        charts=charts_out,
    )

    # Store the full result (not just the dataframe) so /api/session/{id}
    # and the dashboard page can serve it later without recomputing.
    _RESULTS_STORE[session_id] = result
    _SESSION_TIMESTAMPS[session_id] = time.time()

    return result


@router.get("/session/{session_id}", response_model=AnalyzeResponseOut)
async def get_session_result(session_id: str) -> AnalyzeResponseOut:
    """
    EN: Retrieve a previously computed analysis by session_id. Used by the
        dashboard page (and could be used by any other client, e.g. the bot).
    AR: استرجاع نتيجة تحليل سابقة عبر session_id. تُستخدم من صفحة الداشبورد
        (ويمكن استخدامها من أي عميل آخر، مثل البوت).
    """
    _cleanup_expired_sessions()

    result = _RESULTS_STORE.get(session_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="لم يتم العثور على هذا التحليل. قد تكون الجلسة منتهية الصلاحية أو الرابط غير صحيح.",
        )
    return result


@router.get("/health")
async def health_check():
    """EN: Simple health check endpoint. AR: نقطة فحص بسيطة لحالة الخادم."""
    return {"status": "ok"}

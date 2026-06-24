"""
file_loader.py
----------------
EN: Helper to load an uploaded CSV/Excel file into a pandas DataFrame,
    with basic cleanup (drop fully-empty columns/rows, strip whitespace).
AR: دالة مساعدة لتحميل ملف CSV/Excel المرفوع إلى DataFrame مع تنظيف أساسي
    (حذف الأعمدة/الصفوف الفارغة بالكامل، إزالة الفراغات الزائدة).
"""

from __future__ import annotations

import io
import os

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class UnsupportedFileTypeError(Exception):
    """Raised when the uploaded file extension is not supported."""


def load_dataframe(filename: str, file_bytes: bytes) -> pd.DataFrame:
    """
    EN: Load a CSV or Excel file (given as raw bytes) into a DataFrame.
    AR: تحميل ملف CSV أو Excel (كـ bytes) إلى DataFrame.
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"صيغة الملف غير مدعومة: {ext}. الصيغ المدعومة: CSV, XLSX, XLS"
        )

    buffer = io.BytesIO(file_bytes)

    if ext == ".csv":
        # Try a couple of common encodings; CSV files in the wild are messy
        # نحاول أكثر من ترميز شائع لأن ملفات CSV غالباً غير موحّدة
        for encoding in ("utf-8", "utf-8-sig", "cp1256", "latin1"):
            try:
                buffer.seek(0)
                df = pd.read_csv(buffer, encoding=encoding)
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        else:
            raise ValueError("تعذّر قراءة ملف CSV بأي ترميز معروف")
    else:
        df = pd.read_excel(buffer)

    # ---------- Basic cleanup ----------
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(axis=1, how="all")   # drop fully empty columns
    df = df.dropna(axis=0, how="all")   # drop fully empty rows

    # Strip whitespace from string/object columns (covers both legacy "object"
    # dtype and newer pandas "str" dtype)
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip().replace({"nan": None, "None": None})

    if df.empty or df.shape[1] == 0:
        raise ValueError("الملف لا يحتوي على بيانات صالحة للتحليل")

    return df

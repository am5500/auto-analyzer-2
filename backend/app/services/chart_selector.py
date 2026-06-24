"""
chart_selector.py
------------------
EN: Smart logic that inspects a DataFrame's columns and decides which chart
    types are appropriate, based on dtype, number of unique values, and
    whether a column looks like a date.
AR: منطق ذكي يفحص أعمدة DataFrame ويقرر أنواع الرسوم المناسبة بناءً على
    نوع البيانات، عدد القيم الفريدة، ووجود أعمدة تواريخ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

# Threshold below which a text/numeric column is considered "categorical"
# الحد الذي تحت يعتبر فيه العمود "فئوي" (categorical)
CATEGORY_UNIQUE_THRESHOLD = 10

# A text column is considered "long text" (candidate for Word Cloud) if the
# average string length exceeds this number of characters.
# يعتبر العمود النصي "طويلاً" (مرشح لـ Word Cloud) إذا تجاوز متوسط طول النص هذا الرقم
LONG_TEXT_AVG_LEN_THRESHOLD = 25


@dataclass
class ColumnProfile:
    """EN: Metadata describing one column. AR: بيانات وصفية لعمود واحد."""
    name: str
    dtype: str  # "numeric" | "datetime" | "categorical" | "text" | "boolean"
    n_unique: int
    n_missing: int
    sample_values: list = field(default_factory=list)


@dataclass
class ChartSuggestion:
    """EN: One suggested chart with the columns to use. AR: رسم مقترح واحد مع الأعمدة المطلوبة."""
    chart_type: str           # "line" | "bar" | "pie" | "scatter" | "histogram" | "wordcloud"
    x: Optional[str]
    y: Optional[str]
    title: str
    explanation_ar: str
    explanation_en: str
    priority: int = 0         # higher = shown first


def _try_parse_datetime(series: pd.Series) -> bool:
    """
    EN: Try to detect whether a column is actually a date/time column,
        even if pandas loaded it as object/string.
    AR: نحاول معرفة إذا كان العمود تاريخاً حتى لو حُمّل كنص (object).
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return True

    # Only attempt parsing on object/string columns to avoid false positives
    # on numeric columns (e.g. an "age" column of ints shouldn't become a date).
    # NOTE: newer pandas versions may report string columns with dtype "str"
    # (PyArrow-backed) instead of classic "object", so we check both.
    is_text_like = pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)
    if is_text_like:
        sample = series.dropna().astype(str).head(20)
        if sample.empty:
            return False
        try:
            parsed = pd.to_datetime(sample, errors="coerce", format=None)
            # If most of the sample parsed successfully, treat as datetime
            success_ratio = parsed.notna().mean()
            return success_ratio >= 0.8
        except Exception:
            return False
    return False


def profile_dataframe(df: pd.DataFrame) -> List[ColumnProfile]:
    """
    EN: Build a profile for every column: dtype category, unique count, etc.
    AR: بناء ملف تعريفي لكل عمود: نوعه، عدد القيم الفريدة، إلخ.
    """
    profiles: List[ColumnProfile] = []

    for col in df.columns:
        series = df[col]
        n_unique = series.nunique(dropna=True)
        n_missing = int(series.isna().sum())

        if _try_parse_datetime(series):
            dtype = "datetime"
        elif pd.api.types.is_bool_dtype(series):
            dtype = "boolean"
        elif pd.api.types.is_numeric_dtype(series):
            dtype = "numeric"
        elif pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series) or pd.api.types.is_categorical_dtype(series):
            non_null = series.dropna().astype(str)
            avg_len = non_null.str.len().mean() if len(non_null) else 0
            # EN: A column is "free text" if its average string length is long,
            #     regardless of how many unique values it has (a review column
            #     with only 5 distinct long sentences is still free text, not
            #     a small category set).
            # AR: العمود يُعتبر "نصاً حراً" إذا كان متوسط طول النص كبيراً،
            #     بصرف النظر عن عدد القيم الفريدة (عمود مراجعات بـ 5 جمل طويلة
            #     فريدة هو نص حر، لا فئة صغيرة).
            if avg_len and avg_len > LONG_TEXT_AVG_LEN_THRESHOLD:
                dtype = "text"
            else:
                dtype = "categorical"
        else:
            dtype = "categorical"

        profiles.append(
            ColumnProfile(
                name=col,
                dtype=dtype,
                n_unique=int(n_unique),
                n_missing=n_missing,
                sample_values=series.dropna().head(5).tolist(),
            )
        )

    return profiles


def suggest_charts(df: pd.DataFrame, max_suggestions: int = 5) -> List[ChartSuggestion]:
    """
    EN: Core decision engine. Looks at column profiles and proposes between
        3 and `max_suggestions` chart suggestions, ranked by priority.

    AR: محرك القرار الأساسي. يفحص أعمدة البيانات ويقترح من 3 إلى عدد محدد
        من الرسوم البيانية، مرتبة حسب الأولوية.

    Rules implemented / القواعد المطبقة:
      1. date column + numeric column      -> Line Chart
      2. categorical (<10 unique) + numeric -> Bar Chart (and Pie if <=6 categories)
      3. two numeric columns                -> Scatter Plot
      4. one long text column               -> Word Cloud
      5. one numeric column alone           -> Histogram
    """
    profiles = profile_dataframe(df)

    numeric_cols = [p for p in profiles if p.dtype == "numeric"]
    datetime_cols = [p for p in profiles if p.dtype == "datetime"]
    categorical_cols = [p for p in profiles if p.dtype == "categorical" and p.n_unique < CATEGORY_UNIQUE_THRESHOLD]
    text_cols = [p for p in profiles if p.dtype == "text"]

    suggestions: List[ChartSuggestion] = []

    # ---------- Rule 1: Date + Numeric -> Line Chart ----------
    # القاعدة 1: تاريخ + رقم => رسم خطي
    if datetime_cols and numeric_cols:
        date_col = datetime_cols[0]
        for num_col in numeric_cols[:2]:  # limit to first 2 numeric cols to avoid clutter
            suggestions.append(
                ChartSuggestion(
                    chart_type="line",
                    x=date_col.name,
                    y=num_col.name,
                    title=f"{num_col.name} عبر الزمن ({date_col.name})",
                    explanation_ar=(
                        f"يوضح هذا الرسم الخطي تطور قيم '{num_col.name}' بمرور الوقت "
                        f"باستخدام العمود الزمني '{date_col.name}'. مفيد لرصد الاتجاهات "
                        f"(صعود، نزول، تكرار موسمي)."
                    ),
                    explanation_en=(
                        f"This line chart shows how '{num_col.name}' changes over time "
                        f"using the date column '{date_col.name}'. Useful for spotting "
                        f"trends, seasonality, or growth/decline patterns."
                    ),
                    priority=100,
                )
            )

    # ---------- Rule 2: Categorical (<10 unique) + Numeric -> Bar / Pie ----------
    # القاعدة 2: فئوي (أقل من 10 قيم) + رقمي => Bar أو Pie
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        suggestions.append(
            ChartSuggestion(
                chart_type="bar",
                x=cat_col.name,
                y=num_col.name,
                title=f"{num_col.name} حسب {cat_col.name}",
                explanation_ar=(
                    f"يقارن هذا الرسم الشريطي إجمالي/متوسط '{num_col.name}' بين الفئات "
                    f"المختلفة لعمود '{cat_col.name}' ({cat_col.n_unique} فئة). مفيد للمقارنة السريعة."
                ),
                explanation_en=(
                    f"This bar chart compares '{num_col.name}' across the "
                    f"{cat_col.n_unique} categories of '{cat_col.name}'. Good for quick comparison."
                ),
                priority=90,
            )
        )
        # Pie chart only makes sense with a small number of categories (<=6)
        # المخطط الدائري منطقي فقط مع عدد قليل من الفئات (6 أو أقل)
        if cat_col.n_unique <= 6:
            suggestions.append(
                ChartSuggestion(
                    chart_type="pie",
                    x=cat_col.name,
                    y=num_col.name,
                    title=f"توزيع {num_col.name} حسب {cat_col.name}",
                    explanation_ar=(
                        f"يوضح هذا المخطط الدائري النسبة المئوية لكل فئة من '{cat_col.name}' "
                        f"من إجمالي '{num_col.name}'. مناسب لأن عدد الفئات صغير ({cat_col.n_unique})."
                    ),
                    explanation_en=(
                        f"This pie chart shows the percentage share of each category in "
                        f"'{cat_col.name}' relative to total '{num_col.name}'. Suitable because "
                        f"the category count is small ({cat_col.n_unique})."
                    ),
                    priority=70,
                )
            )

    # ---------- Rule 3: Two numeric columns -> Scatter Plot ----------
    # القاعدة 3: عمودان رقميان => Scatter Plot
    if len(numeric_cols) >= 2:
        x_col, y_col = numeric_cols[0], numeric_cols[1]
        suggestions.append(
            ChartSuggestion(
                chart_type="scatter",
                x=x_col.name,
                y=y_col.name,
                title=f"العلاقة بين {x_col.name} و {y_col.name}",
                explanation_ar=(
                    f"يستكشف هذا الرسم المبعثر العلاقة المحتملة بين '{x_col.name}' و '{y_col.name}'. "
                    f"يساعد على رصد الارتباط (موجب/سالب/معدوم) بين المتغيرين."
                ),
                explanation_en=(
                    f"This scatter plot explores the possible relationship between "
                    f"'{x_col.name}' and '{y_col.name}', helping detect correlation patterns."
                ),
                priority=80,
            )
        )

    # ---------- Rule 4: Long text column -> Word Cloud (optional) ----------
    # القاعدة 4: عمود نصي طويل => Word Cloud (اختياري)
    if text_cols:
        t_col = text_cols[0]
        suggestions.append(
            ChartSuggestion(
                chart_type="wordcloud",
                x=t_col.name,
                y=None,
                title=f"سحابة الكلمات لعمود {t_col.name}",
                explanation_ar=(
                    f"يعرض هذا الرسم الكلمات الأكثر تكراراً في العمود النصي '{t_col.name}'. "
                    f"كل كلمة تظهر بحجم أكبر كلما زاد تكرارها."
                ),
                explanation_en=(
                    f"This word cloud highlights the most frequent words in the text "
                    f"column '{t_col.name}'; bigger words appear more often."
                ),
                priority=40,
            )
        )

    # ---------- Rule 5: A single numeric column alone -> Histogram ----------
    # القاعدة 5: عمود رقمي واحد بمفرده => Histogram
    # We add histograms for numeric columns that are not already heavily used above,
    # and always ensure at least one histogram exists if numeric columns are present.
    if numeric_cols:
        # Prefer a numeric column not already used as X/Y in a line/scatter chart, if possible
        used_cols = {s.y for s in suggestions if s.y} | {s.x for s in suggestions if s.x}
        hist_candidates = [c for c in numeric_cols if c.name not in used_cols] or numeric_cols
        hist_col = hist_candidates[0]
        suggestions.append(
            ChartSuggestion(
                chart_type="histogram",
                x=hist_col.name,
                y=None,
                title=f"توزيع القيم لعمود {hist_col.name}",
                explanation_ar=(
                    f"يوضح هذا المدرج التكراري (Histogram) كيفية توزّع قيم '{hist_col.name}' "
                    f"وتكرار كل نطاق من القيم. مفيد لفهم الانتشار والتمركز والقيم الشاذة."
                ),
                explanation_en=(
                    f"This histogram shows how the values of '{hist_col.name}' are "
                    f"distributed across ranges — useful for spotting spread, central "
                    f"tendency, and outliers."
                ),
                priority=60,
            )
        )

    # ---------- Sort by priority and limit to max_suggestions ----------
    # ترتيب حسب الأولوية والاحتفاظ بالعدد المطلوب فقط
    suggestions.sort(key=lambda s: s.priority, reverse=True)

    # Ensure at least 3 if possible, but never exceed max_suggestions
    return suggestions[:max_suggestions]

"""
chart_builder.py
-----------------
EN: Functions that take a DataFrame + a ChartSuggestion and produce a Plotly
    figure, serialized as JSON (so the frontend can render it with Plotly.js).
AR: دوال تأخذ DataFrame + اقتراح رسم (ChartSuggestion) وتُنتج رسماً بصيغة
    Plotly JSON ليعرضه الـ Frontend باستخدام مكتبة Plotly.js.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from app.services.chart_selector import ChartSuggestion

# Basic English+Arabic stopword list for word cloud word-frequency calculation
# قائمة كلمات شائعة (عربي + إنجليزي) لاستثنائها من حساب تكرار الكلمات
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "on", "for",
    "and", "or", "but", "with", "this", "that", "it", "as", "by", "at", "from",
    "في", "من", "إلى", "على", "عن", "مع", "هذا", "هذه", "ذلك", "التي", "الذي",
    "و", "أن", "إن", "كان", "كانت", "ثم",
}


def build_line_chart(df: pd.DataFrame, suggestion: ChartSuggestion) -> go.Figure:
    """EN: Build a line chart (date vs numeric). AR: بناء رسم خطي (تاريخ مقابل رقم)."""
    data = df.copy()
    data[suggestion.x] = pd.to_datetime(data[suggestion.x], errors="coerce")
    data = data.dropna(subset=[suggestion.x, suggestion.y]).sort_values(suggestion.x)
    fig = px.line(
        data,
        x=suggestion.x,
        y=suggestion.y,
        title=suggestion.title,
        markers=True,
    )
    fig.update_layout(template="plotly_white")
    return fig


def build_bar_chart(df: pd.DataFrame, suggestion: ChartSuggestion) -> go.Figure:
    """EN: Build a bar chart (category vs aggregated numeric). AR: بناء رسم شريطي (فئة مقابل رقم مجمّع)."""
    grouped = (
        df.groupby(suggestion.x, dropna=True)[suggestion.y]
        .sum(numeric_only=True)
        .reset_index()
        .sort_values(suggestion.y, ascending=False)
    )
    fig = px.bar(
        grouped,
        x=suggestion.x,
        y=suggestion.y,
        title=suggestion.title,
        text_auto=".2s",
    )
    fig.update_layout(template="plotly_white")
    return fig


def build_pie_chart(df: pd.DataFrame, suggestion: ChartSuggestion) -> go.Figure:
    """EN: Build a pie chart (category share of numeric total). AR: بناء مخطط دائري (نسبة كل فئة)."""
    grouped = (
        df.groupby(suggestion.x, dropna=True)[suggestion.y]
        .sum(numeric_only=True)
        .reset_index()
    )
    fig = px.pie(
        grouped,
        names=suggestion.x,
        values=suggestion.y,
        title=suggestion.title,
        hole=0.35,
    )
    fig.update_layout(template="plotly_white")
    return fig


def build_scatter_chart(df: pd.DataFrame, suggestion: ChartSuggestion) -> go.Figure:
    """EN: Build a scatter plot (numeric vs numeric). AR: بناء رسم مبعثر (رقم مقابل رقم)."""
    data = df.dropna(subset=[suggestion.x, suggestion.y])
    fig = px.scatter(
        data,
        x=suggestion.x,
        y=suggestion.y,
        title=suggestion.title,
        opacity=0.7,
        trendline="ols" if len(data) >= 3 else None,
    )
    fig.update_layout(template="plotly_white")
    return fig


def build_histogram_chart(df: pd.DataFrame, suggestion: ChartSuggestion) -> go.Figure:
    """EN: Build a histogram for a single numeric column. AR: بناء مدرج تكراري لعمود رقمي واحد."""
    data = df.dropna(subset=[suggestion.x])
    fig = px.histogram(
        data,
        x=suggestion.x,
        title=suggestion.title,
        nbins=30,
    )
    fig.update_layout(template="plotly_white", bargap=0.05)
    return fig


def build_wordcloud_chart(df: pd.DataFrame, suggestion: ChartSuggestion) -> go.Figure:
    """
    EN: Build a "word cloud"-style visualization using a Plotly scatter trick
        (word size = frequency), since native word clouds aren't part of Plotly.
    AR: بناء رسم على شكل "سحابة كلمات" باستخدام حيلة Scatter في Plotly
        (حجم الكلمة = عدد تكرارها)، لأن Plotly لا يدعم سحابة الكلمات أصلياً.
    """
    text_series = df[suggestion.x].dropna().astype(str)
    words = []
    for text in text_series:
        tokens = re.findall(r"[A-Za-z\u0600-\u06FF]{3,}", text.lower())
        words.extend([t for t in tokens if t not in STOPWORDS])

    counter = Counter(words)
    top_words = counter.most_common(40)

    if not top_words:
        # Fallback empty figure if no words found
        fig = go.Figure()
        fig.update_layout(title="لا توجد كلمات كافية لإنشاء سحابة كلمات")
        return fig

    import random
    random.seed(42)

    words_list, counts = zip(*top_words)
    max_count = max(counts)
    sizes = [15 + (c / max_count) * 60 for c in counts]
    x_positions = [random.uniform(0, 10) for _ in words_list]
    y_positions = [random.uniform(0, 10) for _ in words_list]

    fig = go.Figure(
        data=[
            go.Scatter(
                x=x_positions,
                y=y_positions,
                mode="text",
                text=words_list,
                textfont=dict(size=sizes),
                hovertext=[f"{w}: {c} مرة" for w, c in zip(words_list, counts)],
                hoverinfo="text",
            )
        ]
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(title=suggestion.title, template="plotly_white")
    return fig


# Map chart_type -> builder function
# تطابق نوع الرسم مع الدالة المسؤولة عن بنائه
CHART_BUILDERS = {
    "line": build_line_chart,
    "bar": build_bar_chart,
    "pie": build_pie_chart,
    "scatter": build_scatter_chart,
    "histogram": build_histogram_chart,
    "wordcloud": build_wordcloud_chart,
}


def render_chart_to_json(df: pd.DataFrame, suggestion: ChartSuggestion) -> Optional[str]:
    """
    EN: Build the figure for a given suggestion and serialize to Plotly JSON.
        Returns None if the chart could not be built (e.g. bad data).
    AR: بناء الرسم حسب الاقتراح وتحويله إلى JSON متوافق مع Plotly.js.
        يرجع None في حال فشل بناء الرسم (بيانات غير صالحة مثلاً).
    """
    builder = CHART_BUILDERS.get(suggestion.chart_type)
    if builder is None:
        return None
    try:
        fig = builder(df, suggestion)
        return pio.to_json(fig)
    except Exception as exc:  # noqa: BLE001
        # In production, log this properly instead of silently failing
        print(f"[chart_builder] Failed to build {suggestion.chart_type} chart: {exc}")
        return None

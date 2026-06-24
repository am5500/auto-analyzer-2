# 📊 محلل البيانات الذكي | Auto Data Analyzer

نظام SaaS لتحليل البيانات تلقائياً: يرفع المستخدم ملف CSV أو Excel، وبدون أي
تدخل بشري في اختيار المحاور أو نوع الرسم، يحلل النظام الأعمدة ويقرر تلقائياً
أفضل 3-5 رسوم بيانية مناسبة، مع تفسير نصي بالعربية والإنجليزية لكل رسم.

An automatic data-analysis SaaS system: the user uploads a CSV/Excel file,
and — with zero manual axis/chart selection — the system inspects the
columns and decides on the 3–5 best chart types, each with a bilingual
explanation.

---

## 🗂️ هيكل المشروع | Project Structure

```
auto-analyzer/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entrypoint (+ /dashboard/{id} route)
│   │   ├── routers/
│   │   │   └── analysis.py          # /api/analyze, /api/session/{id}, /api/health
│   │   └── services/
│   │       ├── file_loader.py       # CSV/Excel loading + cleanup
│   │       ├── chart_selector.py    # 🧠 smart chart-type decision engine
│   │       └── chart_builder.py     # Plotly figure builders
│   └── requirements.txt
├── frontend/
│   ├── index.html                   # Upload UI (RTL Arabic)
│   └── dashboard.html                # Shareable report page (reads ?session_id)
├── telegram_bot/
│   ├── bot.py                        # Telegram bot — forwards files to backend
│   └── requirements.txt
├── Dockerfile                        # Backend image
├── Dockerfile.bot                    # Telegram bot image (separate service)
├── .dockerignore
└── README.md
```

---

## ⚙️ المتطلبات | Requirements

- Python 3.10+ (موصى به 3.11)
- pip
- (اختياري) Docker، إذا رغبت بالنشر كحاوية

---

## 🚀 التشغيل المحلي خطوة بخطوة | Local Setup Step-by-Step

### 1. فك ضغط المشروع والانتقال لمجلده
```bash
cd auto-analyzer
```

### 2. إنشاء بيئة Python افتراضية (موصى به)
```bash
python3 -m venv venv

# تفعيل البيئة على Linux/macOS:
source venv/bin/activate

# تفعيل البيئة على Windows:
venv\Scripts\activate
```

### 3. تثبيت المتطلبات
```bash
cd backend
pip install -r requirements.txt
```

### 4. تشغيل الخادم (Backend)
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

سترى رسالة:
```
Uvicorn running on http://0.0.0.0:8000
```

### 5. فتح الواجهة
افتح المتصفح على:
```
http://localhost:8000
```

الواجهة الأمامية (frontend/index.html) تُعرض تلقائياً من نفس الخادم — لا حاجة
لتشغيل خادم منفصل للـ Frontend.

### 6. الاستخدام
1. اضغط "اختر ملفاً" أو اسحب ملف CSV/Excel إلى الصفحة.
2. اضغط زر "🔍 تحليل البيانات".
3. انتظر ثانيتين — ستظهر 3-5 رسوم بيانية مع تفسير لكل رسم.

---

## 🐳 التشغيل عبر Docker | Running with Docker

### 1. بناء الصورة (Image)
```bash
docker build -t auto-analyzer .
```

### 2. تشغيل الحاوية (Container)
```bash
docker run -p 8000:8000 auto-analyzer
```

### 3. فتح المتصفح
```
http://localhost:8000
```

---

## 🧠 كيف يقرر النظام نوع الرسم؟ | How does the system choose chart types?

يفحص `chart_selector.py` كل عمود ويصنّفه إلى: `numeric` / `datetime` /
`categorical` / `text` / `boolean`. بعدها يطبّق هذه القواعد بالترتيب:

| الحالة | الشرط | الرسم الناتج |
|---|---|---|
| تاريخ + رقم | عمود تاريخ وعمود رقمي واحد على الأقل | **Line Chart** |
| فئة + رقم | عمود نصي بأقل من 10 قيم فريدة + رقمي | **Bar Chart** (و **Pie** إذا ≤6 فئات) |
| رقم + رقم | عمودان رقميان أو أكثر | **Scatter Plot** (مع خط اتجاه OLS) |
| نص حر طويل | متوسط طول النص > 25 حرف | **Word Cloud** (تقريبي عبر Plotly) |
| رقم واحد فقط | لا يوجد فئة/تاريخ مناسب | **Histogram** |

النظام يرتب الاقتراحات حسب `priority` ويعرض أعلى 5 كحد أقصى.

---

## 🔌 واجهة API | API Reference

### `POST /api/analyze`
رفع ملف وإرجاع الرسوم المقترحة.

**Request:** `multipart/form-data` مع حقل `file`

**Response (مثال):**
```json
{
  "session_id": "uuid...",
  "n_rows": 60,
  "n_columns": 4,
  "columns": ["order_date", "region", "revenue", "units"],
  "charts": [
    {
      "chart_type": "line",
      "title": "revenue عبر الزمن (order_date)",
      "explanation_ar": "...",
      "explanation_en": "...",
      "figure_json": "{...Plotly figure JSON...}"
    }
  ]
}
```

### `GET /api/health`
فحص صحة الخادم → `{"status": "ok"}`

### وثائق تفاعلية (Swagger)
بعد تشغيل الخادم، افتح:
```
http://localhost:8000/docs
```

---

## 🤖 بوت تليجرام | Telegram Bot

يسمح للمستخدم برفع ملف CSV/Excel **مباشرة داخل تليجرام**، فيرد عليه البوت
برابط داشبورد فيه كل الرسوم التفاعلية — بدون فتح متصفح لرفع الملف.

البوت **لا يعيد تنفيذ أي منطق تحليل** — هو عميل خفيف (thin client) يبعت
الملف لنفس `/api/analyze` في الـ Backend، ثم يبني رابط `/dashboard/{session_id}`.

```
telegram_bot/
├── bot.py             # سكريبت البوت
└── requirements.txt
```

### كيف يعمل التدفق بالكامل

```
المستخدم في تليجرام
      │  (يرفع ملف CSV/Excel)
      ▼
   bot.py  ──POST /api/analyze──▶  FastAPI Backend
      │                                  │
      │◀──────── session_id ────────────┘
      ▼
  يرد على المستخدم برابط:
  https://your-backend.com/dashboard/{session_id}
      │
      ▼
المستخدم يفتح الرابط في المتصفح
      │
      ▼
صفحة dashboard.html تجلب /api/session/{id}
وتعرض كل الرسوم تفاعلية (Plotly)
```

### 1. إنشاء البوت والحصول على التوكن

1. افتح تليجرام وابحث عن **@BotFather**.
2. اكتب `/newbot` واتبع التعليمات (اسم البوت + username ينتهي بـ `bot`).
3. ستحصل على توكن شكله:
   ```
   123456789:ABCdefGhIJKlmNoPQRstuVWXyz
   ```
4. احتفظ به — لن تحتاج لإظهاره مرة أخرى لاحقاً إلا من BotFather.

### 2. التشغيل المحلي للبوت

```bash
cd telegram_bot
pip install -r requirements.txt

# على Linux/macOS:
export TELEGRAM_BOT_TOKEN="التوكن_بتاعك"
export BACKEND_URL="http://localhost:8000"   # أو رابط الـ Backend المنشور

# على Windows (PowerShell):
$env:TELEGRAM_BOT_TOKEN="التوكن_بتاعك"
$env:BACKEND_URL="http://localhost:8000"

python bot.py
```

**مهم:** لازم الـ Backend (FastAPI) يكون شغّال فعلاً (محلياً أو منشور) قبل
تشغيل البوت، لأن البوت بيبعت الملفات له.

### 3. تجربة البوت

1. افتح تليجرام وابحث عن البوت بالـ username اللي اخترته.
2. اضغط `/start`.
3. ابعت ملف CSV أو Excel.
4. بعد ثوانٍ، هتستلم رابط داشبورد — افتحه في المتصفح.

### 4. نشر البوت مجاناً (Render)

البوت عملية مستقلة شغّالة باستمرار (polling)، فهيكون **Background Worker**
منفصل عن خدمة الـ Backend، مش Web Service.

1. على **render.com** اضغط **New +** → **Background Worker**.
2. اختر نفس مستودع GitHub.
3. في إعدادات البناء:
   - **Dockerfile Path:** `Dockerfile.bot`
4. في **Environment Variables** أضف:
   - `TELEGRAM_BOT_TOKEN` = التوكن بتاعك
   - `BACKEND_URL` = رابط الـ Backend المنشور (مثلاً `https://auto-analyzer.onrender.com`)
5. اضغط **Create Background Worker**.

⚠️ **ملاحظة:** الخطة المجانية لـ Background Workers على Render قد لا تكون
متاحة دائماً بنفس الشروط — تحقق من صفحة الأسعار الحالية. لو لم تكن متاحة
مجاناً، يمكنك تشغيل `bot.py` مجاناً على منصات مثل **PythonAnywhere** (Always-On Task)
أو على أي VPS صغير، أو حتى على جهازك الشخصي مع تشغيله بشكل دائم عبر `screen`/`tmux`.

### 5. ملاحظات مهمة

- البوت يعتمد على إن الـ Backend شغّال ومتاح من الإنترنت (`BACKEND_URL` لازم يكون رابط عام، مش `localhost`، إلا لو بتجرب محلياً).
- روابط الداشبورد صالحة لمدة 24 ساعة فقط (التخزين بالذاكرة — راجع ملاحظات الإنتاج تحت).
- لو الـ Backend على خطة مجانية بها "نوم" (Render Free)، أول طلب من البوت بعد فترة خمول قد يستغرق دقيقة تقريباً.

---


هذا المشروع جاهز للتجربة والتطوير المحلي. قبل النشر التجاري الحقيقي، يُنصح بـ:

- استبدال الذاكرة المؤقتة (`_RESULTS_STORE` في `analysis.py`) بـ Redis أو
  قاعدة بيانات حقيقية. هذا **مهم خصوصاً** مع بوت تليجرام: لو الـ Backend
  عنده أكثر من Worker/Instance، التخزين بالذاكرة لا يُشارك بينهم، وقد يحصل
  المستخدم على "404" عند فتح رابط الداشبورد لو وصل طلبه لـ Instance مختلف
  عن الذي حلّل ملفه.
- تقييد `allow_origins` في CORS بدل `"*"`.
- إضافة مصادقة (Authentication) للمستخدمين.
- إضافة حد لعدد الطلبات (Rate Limiting).
- استخدام تخزين سحابي (S3 مثلاً) بدل الاعتماد على الذاكرة للملفات الكبيرة.
- مراقبة الأخطاء بأداة مثل Sentry بدل `print()`.

---

## 📦 الحزم المستخدمة | Key Dependencies

- **FastAPI** — REST API framework
- **Pandas** — قراءة ومعالجة البيانات
- **Plotly** — رسوم بيانية تفاعلية
- **Statsmodels** — خط الاتجاه (trendline) في Scatter Plot
- **Plotly.js** (CDN) — عرض الرسوم في المتصفح

---

صُمم هذا المشروع كنقطة بداية واضحة وقابلة للتوسع — وليس كحل نهائي جاهز للإنتاج
المباشر دون مراجعة أمنية وهندسية إضافية.

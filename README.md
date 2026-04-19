# 🌿 لكجري نيش | Luxury Niche — تحويل المحتوى بالذكاء الاصطناعي

تطبيق Streamlit لتحويل ملفات **مهووس** إلى تنسيق **لكجري نيش** باستخدام GPT-4o.

## المتطلبات
- Python 3.9+
- مفتاح OpenAI API

## التشغيل المحلي

```bash
pip install -r requirements.txt
streamlit run app.py
```

## النشر على Streamlit Cloud

1. ارفع المجلد على GitHub (repo عام أو خاص)
2. اذهب إلى [share.streamlit.io](https://share.streamlit.io)
3. اربط الـ repo واختر `app.py` كملف رئيسي
4. أضف `OPENAI_API_KEY` في **Secrets** (اختياري — يمكن إدخاله من الواجهة)

## الملفات

| الملف | الوصف |
|-------|-------|
| `app.py` | التطبيق الرئيسي |
| `requirements.txt` | المكتبات المطلوبة |
| `.streamlit/config.toml` | إعدادات Streamlit (ألوان، سيرفر) |

## المميزات

- 🧴 تحويل أوصاف المنتجات بـ HTML احترافي
- 🏷️ تحويل بيانات الماركات وعناوين SEO
- 📂 تحويل التصنيفات وأوصاف SEO
- 🔄 دعم CSV و XLSX بترميز UTF-8 و CP1256
- ⚡ معالجة دُفعية مع شريط تقدم

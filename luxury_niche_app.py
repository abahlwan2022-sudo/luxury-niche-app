"""
تطبيق لكجري نيش - تحويل وصف المنتجات والماركات والتصنيفات
يحول ملفات مهووس إلى تنسيق لكجري نيش باستخدام الذكاء الاصطناعي
"""

import streamlit as st
import pandas as pd
import json
import re
import io
import time
from openai import OpenAI

# ─── إعدادات الصفحة ───────────────────────────────────────────────
st.set_page_config(
    page_title="لكجري نيش | تحويل المنتجات",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS مخصص للدعم العربي ──────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Tajawal', sans-serif; direction: rtl; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; font-weight: 600; }
    .success-box { background: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px; padding: 12px 16px; color: #155724; margin: 8px 0; }
    .error-box   { background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; padding: 12px 16px; color: #721c24; margin: 8px 0; }
    .info-box    { background: #d1ecf1; border: 1px solid #bee5eb; border-radius: 8px; padding: 12px 16px; color: #0c5460; margin: 8px 0; }
    .stat-card   { background: #fff; border: 1px solid #dee2e6; border-radius: 10px; padding: 16px; text-align: center; }
</style>
""", unsafe_allow_html=True)

STORE_NAME = "لكجري نيش | Luxury Niche"
STORE_NAME_AR = "لكجري نيش"
OLD_STORE_NAMES = ["مهووس", "mahwous", "Mahwous", "MAHWOUS"]

# ─── الشريط الجانبي ─────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ الإعدادات")
    st.divider()
    api_key = st.text_input("🔑 مفتاح OpenAI API", type="password", placeholder="sk-...")
    model_choice = st.selectbox("نموذج الذكاء الاصطناعي", ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"])
    batch_size = st.slider("حجم الدفعة (عدد المنتجات في كل طلب)", 1, 5, 1)
    st.divider()
    st.markdown("""
    **تعليمات الاستخدام:**
    1. أدخل مفتاح API
    2. اختر التبويب المطلوب
    3. ارفع الملف
    4. اضغط تحويل
    5. حمّل الملف الناتج
    """)

# ─── دوال مساعدة ────────────────────────────────────────────────────

def get_client(key: str) -> OpenAI:
    return OpenAI(api_key=key)


def replace_store_name(text: str) -> str:
    if not isinstance(text, str):
        return text
    for old in OLD_STORE_NAMES:
        text = re.sub(re.escape(old), STORE_NAME_AR, text, flags=re.IGNORECASE)
    return text


def call_ai(client: OpenAI, model: str, system_prompt: str, user_content: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.4,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise e


def safe_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"لم يمكن تحليل JSON:\n{raw[:300]}")


# ─── وظيفة: تحويل الماركات ──────────────────────────────────────────

def transform_brand(client: OpenAI, model: str, row: pd.Series) -> dict:
    system = f"""أنت خبير في كتابة محتوى العطور الفاخرة باللغة العربية لمتجر "{STORE_NAME}".
مهمتك تحويل بيانات الماركة من متجر مهووس لتناسب هوية لكجري نيش الفاخرة.
أجب دائماً بـ JSON صحيح فقط."""

    user = f"""حوّل بيانات الماركة التالية لتناسب متجر "{STORE_NAME}":

اسم الماركة: {row.get('اسم الماركة', '')}
الوصف الحالي: {row.get('نص تعريف عن الماركة', '')}
عنوان SEO الحالي: {row.get('(Page Title) عنوان صفحة الماركة للسيو', '')}
رابط SEO الحالي: {row.get('(SEO Page URL) رابط صفحة الماركة للسيو', '')}
وصف SEO الحالي: {row.get('(Page Description) وصف صفحة الماركة للسيو', '')}

القواعد:
1. لا تغيّر اسم الماركة أبداً
2. احذف أي ذكر لـ "مهووس" أو "mahwous" واستبدله بـ "{STORE_NAME_AR}"
3. اكتب وصفاً احترافياً غنياً (150-250 كلمة) يليق بمتجر فاخر
4. عنوان Page Title: [اسم الماركة] | [ما يميزها] - {STORE_NAME_AR}
5. وصف SEO: جملتان احترافيتان، أقل من 160 حرفاً
6. رابط SEO: اتركه كما هو (لا تغيّره)

أجب بـ JSON بالمفاتيح:
brand_name, short_description, page_title, seo_url, page_description"""

    result = safe_json(call_ai(client, model, system, user))
    return result


# ─── وظيفة: تحويل التصنيفات ─────────────────────────────────────────

def transform_category(client: OpenAI, model: str, row: pd.Series) -> dict:
    system = f"""أنت خبير SEO ومحتوى متخصص في العطور الفاخرة لمتجر "{STORE_NAME}".
مهمتك تحسين بيانات التصنيف لتعكس هوية لكجري نيش. أجب بـ JSON فقط."""

    user = f"""حسّن بيانات التصنيف التالية لمتجر "{STORE_NAME}":

التصنيف: {row.get('التصنيف', '')}
التصنيف الأعلى: {row.get('التصنيف الأعلى', '')}
عنوان SEO الحالي: {row.get('عنوان صفحة التصنيف (Page Title)', '')}
رابط الصفحة: {row.get('رابط صفحة التصنيف (Page Link)', '')}
وصف SEO الحالي: {row.get('وصف صفحة التصنيف (Page Description)', '')}

القواعد:
1. لا تغيّر اسم التصنيف ورابط الصفحة أبداً
2. احذف أي ذكر لـ "مهووس" واستبدله بـ "{STORE_NAME_AR}"
3. عنوان Page Title: [اسم التصنيف] الفاخر | [وصف مغري] | {STORE_NAME_AR}
4. وصف SEO: جملتان احترافيتان تحتويان على الكلمة المفتاحية، أقل من 160 حرفاً

أجب بـ JSON بالمفاتيح:
category_name, page_title, page_link, page_description"""

    result = safe_json(call_ai(client, model, system, user))
    return result


# ─── وظيفة: تحويل المنتجات ──────────────────────────────────────────

PRODUCT_DESC_SYSTEM = f"""أنت كاتب محتوى متخصص في العطور الفاخرة لمتجر "{STORE_NAME}".
مهمتك تحويل وصف منتجات العطور إلى محتوى HTML احترافي يليق بمتجر فاخر.
أجب دائماً بـ JSON صحيح فقط - لا تضع نصاً خارج JSON."""

PRODUCT_DESC_TEMPLATE = """حوّل بيانات المنتج التالية إلى محتوى احترافي لمتجر "{store}":

اسم المنتج: {name}
اسم الماركة: {brand}
التصنيف: {category}
الوصف الحالي (HTML): {desc}
الحجم/الكمية: {size}
نوع العطر: {perfume_type}
عائلة العطر: {family}
رقم SKU: {sku}
رابط الصورة: {image}

القواعد الصارمة:
1. احذف كل ذكر لـ "مهووس" واستبدله بـ "{store_ar}"
2. اسم المنتج الجديد: احتفظ بالمعلومات الأساسية وأضف "| {store_ar}" في العنوان الميتا فقط
3. الوصف HTML: استخدم h3, p, ul, li, strong فقط - هيكل احترافي واضح
4. هيكل الوصف المطلوب:
   - عنوان h3: اسم العطر ووصف مبدع
   - فقرة افتتاحية (80-120 كلمة): قصة العطر وانطباع أول
   - قسم "مكونات العطر": قمة/قلب/قاعدة بـ ul/li
   - قسم "المعلومات التقنية": الماركة، التركيز، الجنس، الحجم، عائلة العطر بـ ul/li
   - فقرة ختامية: لماذا تختار "{store_ar}"
5. عنوان ميتا: [اسم المنتج] | [ميزة مميزة] | {store_ar} (أقل من 70 حرفاً)

أجب بـ JSON بالمفاتيح:
product_name, meta_title, description_html"""


def transform_product(client: OpenAI, model: str, row: pd.Series) -> dict:
    # استخراج الأعمدة بمرونة
    name = row.get('اسم المنتج') or row.get('اسم ال') or row.get('اسم_المنتج') or ''
    brand = row.get('الماركة') or row.get('الماركة المخصصة') or ''
    category = row.get('فئات المنتج') or row.get('التصنيف') or ''
    desc = row.get('وصف') or ''
    size = row.get('الحجم') or row.get('وزن') or ''
    perfume_type = row.get('نوع العطر') or row.get('نوع المنتج') or ''
    family = row.get('عائلة العطر') or ''
    sku = row.get('رقم المنتج sku') or row.get('رمز المنتج') or ''
    image = row.get('رابط الصورة #') or row.get('رابط المنتج') or ''

    user = PRODUCT_DESC_TEMPLATE.format(
        store=STORE_NAME,
        store_ar=STORE_NAME_AR,
        name=name, brand=brand, category=category, desc=str(desc)[:800],
        size=size, perfume_type=perfume_type, family=family, sku=sku, image=image,
    )

    result = safe_json(call_ai(client, model, PRODUCT_DESC_SYSTEM, user))
    return result


# ─── دالة قراءة الملفات بمرونة ──────────────────────────────────────

def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith('.csv'):
        # جرب utf-8-sig أولاً ثم cp1256
        try:
            return pd.read_csv(uploaded_file, encoding='utf-8-sig')
        except Exception:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding='cp1256')
    elif name.endswith('.xlsx') or name.endswith('.xls'):
        # تحقق هل الصف الأول هو header أم لا
        df_check = pd.read_excel(uploaded_file, nrows=2)
        uploaded_file.seek(0)
        # إذا كان الصف الأول "رقم" يحتوي على No. أو بيانات رقمية، اقرأ من header=1
        first_val = str(list(df_check.columns)[0]).strip()
        if first_val in ['رقم', 'No.', 'رقم المنتج'] or re.match(r'^\d+$', first_val):
            return pd.read_excel(uploaded_file, header=1)
        return pd.read_excel(uploaded_file)
    else:
        raise ValueError("صيغة الملف غير مدعومة. استخدم CSV أو XLSX.")


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, encoding='utf-8-sig')
    return buffer.getvalue()


# ─── الواجهة الرئيسية ───────────────────────────────────────────────

st.title("🌿 لكجري نيش | تحويل المحتوى بالذكاء الاصطناعي")
st.caption("حوّل ملفات مهووس إلى تنسيق لكجري نيش باحترافية تامة — منتجات، ماركات، تصنيفات")
st.divider()

tab_products, tab_brands, tab_categories = st.tabs([
    "🧴 تحويل المنتجات",
    "🏷️ تحويل الماركات",
    "📂 تحويل التصنيفات",
])

# ══════════════════════════════════════════════════════════════════════
# تبويب: المنتجات
# ══════════════════════════════════════════════════════════════════════
with tab_products:
    st.subheader("تحويل وصف المنتجات")
    st.markdown("""
    <div class="info-box">
    ارفع ملف المنتجات (CSV أو XLSX) وسيقوم التطبيق بتحويل الأوصاف واسترداد التنسيق الكامل لمتجر لكجري نيش.
    </div>
    """, unsafe_allow_html=True)

    uploaded_products = st.file_uploader(
        "ارفع ملف المنتجات", type=["csv", "xlsx", "xls"],
        key="products_uploader"
    )

    if uploaded_products:
        try:
            df_prod = read_uploaded_file(uploaded_products)
            # توحيد أسماء الأعمدة (إزالة المسافات الزائدة)
            df_prod.columns = [str(c).strip() for c in df_prod.columns]

            st.success(f"تم تحميل الملف: {len(df_prod)} منتج")
            st.dataframe(df_prod.head(3), use_container_width=True)

            # تحديد عمود الاسم
            name_col_candidates = ['اسم المنتج', 'اسم ال', 'اسم_المنتج', 'اسم الـ', 'اسم']
            name_col = next((c for c in name_col_candidates if c in df_prod.columns), None)
            if name_col is None and len(df_prod.columns) > 1:
                name_col = df_prod.columns[1]

            col1, col2 = st.columns(2)
            start_row = col1.number_input("ابدأ من السطر رقم", min_value=1, max_value=len(df_prod), value=1) - 1
            end_row = col2.number_input("حتى السطر رقم", min_value=1, max_value=len(df_prod), value=min(5, len(df_prod)))

            if st.button("🚀 بدء التحويل", key="convert_products", type="primary"):
                if not api_key:
                    st.error("أدخل مفتاح API أولاً في الشريط الجانبي")
                    st.stop()

                client = get_client(api_key)
                subset = df_prod.iloc[start_row:end_row].copy()
                results = []
                errors = []

                progress = st.progress(0)
                status_text = st.empty()
                total = len(subset)

                for idx, (i, row) in enumerate(subset.iterrows()):
                    product_name = row.get(name_col, f"منتج {i+1}") if name_col else f"منتج {i+1}"
                    status_text.text(f"جاري معالجة: {product_name} ({idx+1}/{total})")
                    try:
                        transformed = transform_product(client, model_choice, row)
                        new_row = row.copy()
                        # تطبيق النتائج على الأعمدة المناسبة
                        if name_col and 'product_name' in transformed:
                            new_row[name_col] = transformed['product_name']
                        if 'وصف' in new_row.index:
                            new_row['وصف'] = transformed.get('description_html', new_row['وصف'])
                        if 'عنوان ميتا المنتج' in new_row.index:
                            new_row['عنوان ميتا المنتج'] = transformed.get('meta_title', '')
                        # استبدال أسماء المتاجر في جميع الأعمدة النصية
                        for col in new_row.index:
                            new_row[col] = replace_store_name(new_row[col])
                        results.append(new_row)
                    except Exception as e:
                        errors.append(f"سطر {i+1} - {product_name}: {str(e)}")
                        results.append(row)  # احتفظ بالصف الأصلي عند الخطأ

                    progress.progress((idx + 1) / total)
                    if (idx + 1) % batch_size == 0 and idx < total - 1:
                        time.sleep(0.5)

                status_text.text("اكتمل التحويل!")
                df_result = pd.DataFrame(results)

                if errors:
                    st.warning(f"تنبيه: {len(errors)} خطأ أثناء المعالجة:")
                    for err in errors[:5]:
                        st.caption(f"• {err}")

                st.markdown('<div class="success-box">تم التحويل بنجاح!</div>', unsafe_allow_html=True)
                st.dataframe(df_result[[c for c in [name_col, 'وصف', 'عنوان ميتا المنتج'] if c and c in df_result.columns]].head(), use_container_width=True)

                csv_bytes = df_to_csv_bytes(df_result)
                st.download_button(
                    "⬇️ تحميل ملف المنتجات المحوّل",
                    data=csv_bytes,
                    file_name="منتجات لكجري نيش.csv",
                    mime="text/csv",
                )

        except Exception as e:
            st.error(f"خطأ في قراءة الملف: {e}")


# ══════════════════════════════════════════════════════════════════════
# تبويب: الماركات
# ══════════════════════════════════════════════════════════════════════
with tab_brands:
    st.subheader("تحويل بيانات الماركات")
    st.markdown("""
    <div class="info-box">
    ارفع ملف ماركات مهووس (CSV) وسيحول التطبيق الأوصاف وبيانات SEO لتناسب لكجري نيش.
    </div>
    """, unsafe_allow_html=True)

    uploaded_brands = st.file_uploader(
        "ارفع ملف الماركات", type=["csv", "xlsx"],
        key="brands_uploader"
    )

    if uploaded_brands:
        try:
            df_brands = read_uploaded_file(uploaded_brands)
            df_brands.columns = [str(c).strip() for c in df_brands.columns]
            st.success(f"تم تحميل الملف: {len(df_brands)} ماركة")
            st.dataframe(df_brands.head(3), use_container_width=True)

            col1, col2 = st.columns(2)
            b_start = col1.number_input("ابدأ من الماركة رقم", min_value=1, max_value=len(df_brands), value=1) - 1
            b_end = col2.number_input("حتى الماركة رقم", min_value=1, max_value=len(df_brands), value=min(10, len(df_brands)))

            if st.button("🚀 تحويل الماركات", key="convert_brands", type="primary"):
                if not api_key:
                    st.error("أدخل مفتاح API أولاً")
                    st.stop()

                client = get_client(api_key)
                subset = df_brands.iloc[b_start:b_end].copy()
                results = []
                errors = []
                progress = st.progress(0)
                status_text = st.empty()
                total = len(subset)

                for idx, (i, row) in enumerate(subset.iterrows()):
                    brand_name = row.get('اسم الماركة', f'ماركة {i+1}')
                    status_text.text(f"جاري معالجة: {brand_name} ({idx+1}/{total})")
                    try:
                        t = transform_brand(client, model_choice, row)
                        new_row = row.copy()
                        new_row['نص تعريف عن الماركة'] = t.get('short_description', row.get('نص تعريف عن الماركة', ''))
                        new_row['(Page Title) عنوان صفحة الماركة للسيو'] = t.get('page_title', '')
                        new_row['(Page Description) وصف صفحة الماركة للسيو'] = t.get('page_description', '')
                        # لا نغيّر اسم الماركة ورابط SEO
                        results.append(new_row)
                    except Exception as e:
                        errors.append(f"{brand_name}: {str(e)}")
                        results.append(row)

                    progress.progress((idx + 1) / total)
                    time.sleep(0.3)

                status_text.text("اكتمل التحويل!")
                df_result = pd.DataFrame(results)

                if errors:
                    st.warning(f"{len(errors)} خطأ:")
                    for err in errors[:5]:
                        st.caption(f"• {err}")

                st.markdown('<div class="success-box">تم تحويل الماركات بنجاح!</div>', unsafe_allow_html=True)
                preview_cols = [c for c in ['اسم الماركة', 'نص تعريف عن الماركة', '(Page Title) عنوان صفحة الماركة للسيو'] if c in df_result.columns]
                st.dataframe(df_result[preview_cols].head(), use_container_width=True)

                st.download_button(
                    "⬇️ تحميل ماركات لكجري نيش",
                    data=df_to_csv_bytes(df_result),
                    file_name="ماركات لكجري نيش.csv",
                    mime="text/csv",
                )

        except Exception as e:
            st.error(f"خطأ: {e}")


# ══════════════════════════════════════════════════════════════════════
# تبويب: التصنيفات
# ══════════════════════════════════════════════════════════════════════
with tab_categories:
    st.subheader("تحويل التصنيفات")
    st.markdown("""
    <div class="info-box">
    ارفع ملف تصنيفات مهووس (CSV) وسيحافظ التطبيق على أسماء التصنيفات وروابطها ويحسّن عناوين وأوصاف SEO لتعكس هوية لكجري نيش.
    </div>
    """, unsafe_allow_html=True)

    uploaded_cats = st.file_uploader(
        "ارفع ملف التصنيفات", type=["csv", "xlsx"],
        key="cats_uploader"
    )

    if uploaded_cats:
        try:
            df_cats = read_uploaded_file(uploaded_cats)
            df_cats.columns = [str(c).strip() for c in df_cats.columns]
            st.success(f"تم تحميل الملف: {len(df_cats)} تصنيف")
            st.dataframe(df_cats.head(3), use_container_width=True)

            use_ai = st.checkbox("استخدام الذكاء الاصطناعي لتحسين SEO (أبطأ لكن أدق)", value=True)

            col1, col2 = st.columns(2)
            c_start = col1.number_input("ابدأ من التصنيف رقم", min_value=1, max_value=len(df_cats), value=1) - 1
            c_end = col2.number_input("حتى التصنيف رقم", min_value=1, max_value=len(df_cats), value=min(20, len(df_cats)))

            if st.button("🚀 تحويل التصنيفات", key="convert_cats", type="primary"):
                if use_ai and not api_key:
                    st.error("أدخل مفتاح API أولاً")
                    st.stop()

                client = get_client(api_key) if use_ai and api_key else None
                subset = df_cats.iloc[c_start:c_end].copy()
                results = []
                errors = []
                progress = st.progress(0)
                status_text = st.empty()
                total = len(subset)

                for idx, (i, row) in enumerate(subset.iterrows()):
                    cat_name = row.get('التصنيف', f'تصنيف {i+1}')
                    status_text.text(f"جاري معالجة: {cat_name} ({idx+1}/{total})")
                    try:
                        new_row = row.copy()
                        if use_ai and client:
                            t = transform_category(client, model_choice, row)
                            # نحافظ على اسم التصنيف ورابطه دون تغيير
                            title_col = 'عنوان صفحة التصنيف (Page Title)'
                            desc_col = 'وصف صفحة التصنيف (Page Description)'
                            if title_col in new_row.index:
                                new_row[title_col] = t.get('page_title', new_row[title_col])
                            if desc_col in new_row.index:
                                new_row[desc_col] = t.get('page_description', new_row[desc_col])
                        else:
                            # استبدال نصي بسيط بدون AI
                            for col in new_row.index:
                                new_row[col] = replace_store_name(new_row[col])
                        results.append(new_row)
                    except Exception as e:
                        errors.append(f"{cat_name}: {str(e)}")
                        results.append(row)

                    progress.progress((idx + 1) / total)
                    if use_ai:
                        time.sleep(0.3)

                status_text.text("اكتمل التحويل!")
                df_result = pd.DataFrame(results)

                if errors:
                    st.warning(f"{len(errors)} خطأ:")
                    for err in errors[:5]:
                        st.caption(f"• {err}")

                st.markdown('<div class="success-box">تم تحويل التصنيفات بنجاح!</div>', unsafe_allow_html=True)
                preview_cols = [c for c in [
                    'التصنيف', 'عنوان صفحة التصنيف (Page Title)', 'وصف صفحة التصنيف (Page Description)'
                ] if c in df_result.columns]
                st.dataframe(df_result[preview_cols].head(10), use_container_width=True)

                st.download_button(
                    "⬇️ تحميل تصنيفات لكجري نيش",
                    data=df_to_csv_bytes(df_result),
                    file_name="تصنيفات لكجري نيش.csv",
                    mime="text/csv",
                )

        except Exception as e:
            st.error(f"خطأ: {e}")

# ─── تذييل ──────────────────────────────────────────────────────────
st.divider()
st.caption("🌿 لكجري نيش | Luxury Niche — جميع الحقوق محفوظة")

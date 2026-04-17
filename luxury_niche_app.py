"""
لكجري نيش | Luxury Niche — محوّل الهوية التجارية
Transforms Mahwous product/brand data into Luxury Niche identity
"""

import streamlit as st
import pandas as pd
import json
import re
import io
import time
import itertools
from typing import Optional
from bs4 import BeautifulSoup
import anthropic

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="لكجري نيش | محوّل الهوية التجارية",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&display=swap');

html, body, [class*="css"] { font-family: 'Tajawal', sans-serif; }

.brand-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 2rem 3rem;
    border-radius: 16px;
    text-align: center;
    margin-bottom: 2rem;
    border: 1px solid #e8c45a33;
}
.brand-header h1 { color: #e8c45a; font-size: 2.4rem; font-weight: 700; margin: 0; letter-spacing: 2px; }
.brand-header p  { color: #ccc; font-size: 1rem; margin: 0.5rem 0 0; }

.metric-card {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border: 1px solid #e8c45a55;
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
}
.metric-card .number { color: #e8c45a; font-size: 2rem; font-weight: 700; }
.metric-card .label  { color: #aaa; font-size: 0.85rem; margin-top: 4px; }

.success-row { background: #0a2e0a; border-left: 3px solid #4caf50; padding: 6px 12px; margin: 2px 0; border-radius: 4px; font-size: 0.85rem; }
.error-row   { background: #2e0a0a; border-left: 3px solid #f44336; padding: 6px 12px; margin: 2px 0; border-radius: 4px; font-size: 0.85rem; }

.stProgress > div > div { background-color: #e8c45a !important; }

.sidebar-section {
    background: #0f1929;
    border: 1px solid #e8c45a33;
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1rem;
}

div[data-testid="stTabs"] button { font-family: 'Tajawal', sans-serif !important; font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
<div class="brand-header">
    <h1>✨ لكجري نيش | Luxury Niche ✨</h1>
    <p>محوّل الهوية التجارية — من مهووس إلى فخامة لا تضاهى</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Session State Defaults
# ─────────────────────────────────────────────
for key, val in {
    "products_results": [],
    "brands_results": [],
    "products_running": False,
    "brands_running": False,
    "products_stop": False,
    "brands_stop": False,
    "api_key_cycle": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ─────────────────────────────────────────────
# SANITIZER
# ─────────────────────────────────────────────
REPLACEMENTS = [
    (r"مهووس\s*العطور", "لكجري نيش"),
    (r"متجر\s*مهووس", "متجر لكجري نيش"),
    (r"مهووس", "لكجري نيش"),
    (r"Mahwoos\s*Gifts", "Luxury Niche Gifts"),
    (r"mahwous\.com", "luxuryniche.com"),
    (r"mahwous", "luxuryniche"),
    (r"Mahwous", "LuxuryNiche"),
    (r"mahwoos", "luxuryniche"),
    (r"Mahwoos", "LuxuryNiche"),
    (r"عروض\s*لكجري نيش", "عروض لكجري نيش"),   # avoid double replace
]


def sanitize_text(text: str) -> str:
    """Replace all Mahwous references with Luxury Niche."""
    if not isinstance(text, str):
        return text
    for pattern, replacement in REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply sanitizer to all string columns."""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(lambda x: sanitize_text(x) if isinstance(x, str) else x)
    return df


# ─────────────────────────────────────────────
# HTML INGREDIENT EXTRACTOR
# ─────────────────────────────────────────────
def extract_ingredients_from_html(html: str) -> dict:
    """Extract perfume notes / ingredients from HTML using BeautifulSoup."""
    if not isinstance(html, str) or not html.strip():
        return {}
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")

    found = {"top": [], "heart": [], "base": [], "raw_text": ""}

    top_keywords    = ["مقدمة", "البداية", "الافتتاح", "top note", "opening"]
    heart_keywords  = ["قلب", "الجوهر", "الوسط", "heart note", "middle"]
    base_keywords   = ["قاعدة", "الخاتمة", "النهاية", "base note", "dry down"]

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    current_section = "general"
    general_notes = []

    for line in lines:
        ll = line.lower()
        if any(k in ll for k in top_keywords):
            current_section = "top"
        elif any(k in ll for k in heart_keywords):
            current_section = "heart"
        elif any(k in ll for k in base_keywords):
            current_section = "base"
        else:
            if current_section == "top":
                found["top"].append(line)
            elif current_section == "heart":
                found["heart"].append(line)
            elif current_section == "base":
                found["base"].append(line)
            else:
                general_notes.append(line)

    found["raw_text"] = "\n".join(lines[:40])  # first 40 lines as context
    return found


# ─────────────────────────────────────────────
# API KEY MANAGER
# ─────────────────────────────────────────────
def get_api_client(api_keys: list) -> Optional[anthropic.Anthropic]:
    """Return an Anthropic client cycling through keys."""
    if not api_keys:
        return None
    if st.session_state.api_key_cycle is None:
        st.session_state.api_key_cycle = itertools.cycle(api_keys)
    key = next(st.session_state.api_key_cycle)
    return anthropic.Anthropic(api_key=key)


def call_claude(prompt: str, api_keys: list, max_retries: int = 3) -> Optional[str]:
    """Call Claude API with retry + key rotation on rate limit."""
    for attempt in range(max_retries):
        try:
            client = get_api_client(api_keys)
            if not client:
                return None
            message = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except anthropic.RateLimitError:
            if attempt < max_retries - 1:
                # rotate to next key
                st.session_state.api_key_cycle = None
                time.sleep(2)
            else:
                return None
        except Exception as e:
            return None
    return None


# ─────────────────────────────────────────────
# BRAND TRANSFORM PROMPT
# ─────────────────────────────────────────────
def build_brand_prompt(row: dict) -> str:
    brand_name    = sanitize_text(str(row.get("اسم الماركة", "")))
    short_desc    = sanitize_text(str(row.get("وصف مختصر عن الماركة", "")))
    page_title    = sanitize_text(str(row.get("(Page Title) عنوان صفحة العلامة التجارية", "")))
    seo_url       = sanitize_text(str(row.get("(SEO Page URL) رابط صفحة العلامة التجارية", "")))
    meta_desc     = sanitize_text(str(row.get("(Page Description) وصف صفحة العلامة التجارية", "")))

    return f"""أنت خبير في بناء الهوية التجارية لمتجر "لكجري نيش | Luxury Niche"، أحد أرقى متاجر العطور النيش في المملكة العربية السعودية.

مهمتك: تحويل بيانات الماركة التالية إلى هوية "لكجري نيش" الفاخرة الراقية.

**بيانات الماركة الحالية:**
- الاسم: {brand_name}
- الوصف المختصر: {short_desc}
- عنوان الصفحة: {page_title}
- رابط SEO: {seo_url}
- وصف Meta: {meta_desc}

**التعليمات الصارمة:**
1. لا تذكر "مهووس" أو "mahwous" أو أي من مشتقاتها مطلقاً.
2. اكتب "الوصف المطول" بأسلوب نيش فاخر لا يقل عن 250 كلمة.
3. اجعل عنوان الصفحة يعكس هوية "لكجري نيش" مثل: "[اسم الماركة] | فخامة لا تضاهى في لكجري نيش".
4. رابط SEO: استبدل أي ذكر لمهووس بـ luxury-niche.
5. الوصف meta: لا يتجاوز 160 حرفاً، جذاب وخالٍ من مهووس.
6. لغة الكتابة عربية فصحى راقية.

**أعد الناتج بتنسيق JSON صارم فقط (بدون أي نص خارج الـ JSON):**
{{
  "brand_name": "...",
  "short_description": "...",
  "page_title": "...",
  "seo_url": "...",
  "meta_description": "..."
}}"""


# ─────────────────────────────────────────────
# PRODUCT TRANSFORM PROMPT
# ─────────────────────────────────────────────
def build_product_prompt(row: dict) -> str:
    product_name  = sanitize_text(str(row.get("أسم المنتج", "")))
    category      = sanitize_text(str(row.get("تصنيف المنتج", "")))
    brand         = sanitize_text(str(row.get("الماركة", "")))
    raw_html      = str(row.get("الوصف", ""))
    
    ingredients   = extract_ingredients_from_html(raw_html)
    top_notes     = ", ".join(ingredients.get("top", [])) or "غير محدد"
    heart_notes   = ", ".join(ingredients.get("heart", [])) or "غير محدد"
    base_notes    = ", ".join(ingredients.get("base", [])) or "غير محدد"
    raw_context   = sanitize_text(ingredients.get("raw_text", ""))[:1000]

    # Extract image alt text for context
    img_alt       = sanitize_text(str(row.get("وصف صورة المنتج", "")))[:200]
    promo_title   = sanitize_text(str(row.get("العنوان الترويجي", "")))

    return f"""أنت خبير تسويق محتوى عطور لمتجر "لكجري نيش | Luxury Niche".

**بيانات المنتج:**
- اسم المنتج: {product_name}
- الماركة: {brand}
- التصنيف: {category}
- نوتات الرأس: {top_notes}
- نوتات القلب: {heart_notes}
- نوتات القاعدة: {base_notes}
- سياق الوصف الأصلي: {raw_context}

**التعليمات الصارمة:**
1. لا تذكر "مهووس" أو "mahwous" مطلقاً.
2. لا تضع روابط داخلية أو خارجية.
3. لا تذكر SKU أو أرقام تعريفية.
4. استند فقط إلى المكونات المذكورة أعلاه؛ لا تخترع مكونات غير موجودة.
5. اكتب بـ HTML احترافي (استخدم h2, h3, p, ul, li, strong) مناسب لمتجر Salla.
6. لا تستخدم Markdown (لا #، لا **, لا ---).
7. ابدأ مباشرةً بـ HTML بدون أي مقدمة نصية.

**الهيكل المطلوب (HTML):**
<h2>قصة العطر — [عنوان جذاب]</h2>
<p>[سرد إبداعي 3-4 فقرات عن إلهام العطر وفخامته]</p>

<h2>السمفونية العطرية</h2>
<h3>✦ نوتات الرأس</h3>
<p>[وصف حسي للمكونات المذكورة فعلاً]</p>
<h3>✦ نوتات القلب</h3>
<p>[وصف حسي]</p>
<h3>✦ نوتات القاعدة</h3>
<p>[وصف حسي]</p>

<h2>المواصفات الفنية</h2>
<ul>
<li><strong>الماركة:</strong> {brand}</li>
[باقي المواصفات من البيانات المتاحة]
</ul>

<h2>لماذا تختار هذا العطر من لكجري نيش؟</h2>
<p>[3-4 فقرات إقناعية فاخرة]</p>

<p style="text-align:center"><em>لكجري نيش | Luxury Niche — وجهتك الأولى لأفضل العطور النيش الأصلية في السعودية</em></p>"""


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ إعدادات API")
    st.markdown("""
    <div class="sidebar-section">
    أدخل مفاتيح Anthropic API (مفتاح في كل سطر).<br>
    سيتم التدوير بينها تلقائياً للتسريع.
    </div>
    """, unsafe_allow_html=True)

    raw_keys = st.text_area(
        "مفاتيح API",
        placeholder="sk-ant-api03-...\nsk-ant-api03-...",
        height=120,
        label_visibility="collapsed",
    )
    api_keys = [k.strip() for k in raw_keys.strip().splitlines() if k.strip().startswith("sk-")]

    if api_keys:
        st.success(f"✅ {len(api_keys)} مفتاح جاهز")
    else:
        st.warning("⚠️ أدخل مفتاح API واحداً على الأقل")

    st.divider()
    st.markdown("### 🔧 خيارات المعالجة")

    batch_delay = st.slider("تأخير بين الطلبات (ثانية)", 0.5, 5.0, 1.5, 0.5)
    start_from  = st.number_input("ابدأ من السجل رقم", min_value=1, value=1, step=1)

    st.divider()
    st.markdown("### 📊 الإحصاءات")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("منتجات محولة", len(st.session_state.products_results))
    with col2:
        st.metric("ماركات محولة", len(st.session_state.brands_results))


# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab_products, tab_brands, tab_sanitize = st.tabs([
    "🧴 تحويل المنتجات",
    "🏷️ تحويل الماركات",
    "🧹 تطهير فوري (بدون AI)"
])


# ══════════════════════════════════════════════
# TAB 1 — PRODUCTS
# ══════════════════════════════════════════════
with tab_products:
    st.markdown("## 🧴 تحويل المنتجات إلى هوية لكجري نيش")
    st.info("يقوم هذا التبويب بتحويل وصف كل منتج إلى وصف نيش فاخر بالكامل مع استخراج المكونات الحقيقية من HTML.")

    uploaded_products = st.file_uploader(
        "📂 رفع ملف المنتجات (XLSX)",
        type=["xlsx", "xls"],
        key="products_file",
    )

    if uploaded_products:
        try:
            df_raw = pd.read_excel(uploaded_products, header=1)
            df_products = sanitize_dataframe(df_raw)

            total = len(df_products)
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f'<div class="metric-card"><div class="number">{total:,}</div><div class="label">إجمالي المنتجات</div></div>', unsafe_allow_html=True)
            with c2:
                brands_count = df_products["الماركة"].nunique() if "الماركة" in df_products.columns else 0
                st.markdown(f'<div class="metric-card"><div class="number">{brands_count}</div><div class="label">ماركة مختلفة</div></div>', unsafe_allow_html=True)
            with c3:
                done = len(st.session_state.products_results)
                st.markdown(f'<div class="metric-card"><div class="number">{done}</div><div class="label">تم تحويلها</div></div>', unsafe_allow_html=True)
            with c4:
                remaining = total - done
                st.markdown(f'<div class="metric-card"><div class="number">{remaining}</div><div class="label">متبقية</div></div>', unsafe_allow_html=True)

            st.markdown("---")

            # Preview
            with st.expander("👁️ معاينة البيانات (أول 5 صفوف بعد التطهير)"):
                preview_cols = ["أسم المنتج", "الماركة", "تصنيف المنتج"]
                available = [c for c in preview_cols if c in df_products.columns]
                st.dataframe(df_products[available].head(), use_container_width=True)

            col_start, col_stop = st.columns([1, 1])
            with col_start:
                start_btn = st.button("🚀 بدء التحويل بالـ AI", type="primary", use_container_width=True,
                                      disabled=not api_keys or st.session_state.products_running)
            with col_stop:
                stop_btn = st.button("⏹️ إيقاف", use_container_width=True,
                                     disabled=not st.session_state.products_running)

            if stop_btn:
                st.session_state.products_stop = True
                st.session_state.products_running = False

            if start_btn and api_keys:
                st.session_state.products_running = True
                st.session_state.products_stop = False
                st.session_state.api_key_cycle = None

                progress_bar = st.progress(0)
                status_area  = st.empty()
                log_area     = st.container()

                start_idx = max(0, start_from - 1)
                rows_to_process = df_products.iloc[start_idx:]
                already_done = {r["original_index"] for r in st.session_state.products_results}

                for i, (idx, row) in enumerate(rows_to_process.iterrows()):
                    if st.session_state.products_stop:
                        st.warning("⏹️ تم إيقاف المعالجة.")
                        break

                    if idx in already_done:
                        continue

                    product_name = str(row.get("أسم المنتج", f"منتج #{idx}"))
                    status_area.markdown(f"**⏳ جاري معالجة:** {product_name} ({i+1}/{len(rows_to_process)})")

                    prompt   = build_product_prompt(row.to_dict())
                    response = call_claude(prompt, api_keys)

                    result_row = row.to_dict()
                    result_row["original_index"] = idx

                    if response:
                        result_row["الوصف"] = response
                        st.session_state.products_results.append(result_row)
                        with log_area:
                            st.markdown(f'<div class="success-row">✅ {product_name}</div>', unsafe_allow_html=True)
                    else:
                        # Keep original sanitized
                        st.session_state.products_results.append(result_row)
                        with log_area:
                            st.markdown(f'<div class="error-row">⚠️ {product_name} (تم تطهيره فقط)</div>', unsafe_allow_html=True)

                    progress = min((i + 1) / len(rows_to_process), 1.0)
                    progress_bar.progress(progress)
                    time.sleep(batch_delay)

                st.session_state.products_running = False
                st.success(f"✅ اكتملت المعالجة! تم تحويل {len(st.session_state.products_results)} منتج.")

            # Download
            if st.session_state.products_results:
                st.markdown("---")
                st.markdown("### 📥 تنزيل النتائج")

                result_df = pd.DataFrame(st.session_state.products_results)
                result_df.drop(columns=["original_index"], errors="ignore", inplace=True)

                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        result_df.to_excel(writer, index=False, sheet_name="منتجات لكجري نيش")
                    st.download_button(
                        "⬇️ تنزيل Excel",
                        data=buf.getvalue(),
                        file_name="luxury_niche_products.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                with col_dl2:
                    csv_buf = result_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                    st.download_button(
                        "⬇️ تنزيل CSV",
                        data=csv_buf,
                        file_name="luxury_niche_products.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

                with st.expander("👁️ معاينة النتائج"):
                    preview_cols = ["أسم المنتج", "الماركة", "تصنيف المنتج"]
                    av = [c for c in preview_cols if c in result_df.columns]
                    st.dataframe(result_df[av].head(10), use_container_width=True)

                if st.button("🗑️ مسح النتائج وإعادة البدء", type="secondary"):
                    st.session_state.products_results = []
                    st.rerun()

        except Exception as e:
            st.error(f"❌ خطأ في قراءة الملف: {e}")


# ══════════════════════════════════════════════
# TAB 2 — BRANDS
# ══════════════════════════════════════════════
with tab_brands:
    st.markdown("## 🏷️ تحويل الماركات إلى هوية لكجري نيش")
    st.info("يقوم هذا التبويب بتحويل بيانات كل ماركة إلى هوية فاخرة لمتجر لكجري نيش.")

    uploaded_brands = st.file_uploader(
        "📂 رفع ملف الماركات (CSV)",
        type=["csv"],
        key="brands_file",
    )

    if uploaded_brands:
        try:
            df_brands_raw = pd.read_csv(uploaded_brands)
            df_brands = sanitize_dataframe(df_brands_raw)

            total_brands = len(df_brands)
            done_brands  = len(st.session_state.brands_results)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="metric-card"><div class="number">{total_brands}</div><div class="label">إجمالي الماركات</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="metric-card"><div class="number">{done_brands}</div><div class="label">تم تحويلها</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="metric-card"><div class="number">{total_brands - done_brands}</div><div class="label">متبقية</div></div>', unsafe_allow_html=True)

            st.markdown("---")

            with st.expander("👁️ معاينة الماركات (أول 5)"):
                st.dataframe(df_brands[["اسم الماركة", "(Page Title) عنوان صفحة العلامة التجارية"]].head(), use_container_width=True)

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                start_brands_btn = st.button("🚀 بدء تحويل الماركات", type="primary", use_container_width=True,
                                             disabled=not api_keys or st.session_state.brands_running)
            with col_b2:
                stop_brands_btn = st.button("⏹️ إيقاف", key="stop_brands", use_container_width=True,
                                            disabled=not st.session_state.brands_running)

            if stop_brands_btn:
                st.session_state.brands_stop = True
                st.session_state.brands_running = False

            if start_brands_btn and api_keys:
                st.session_state.brands_running = True
                st.session_state.brands_stop = False
                st.session_state.api_key_cycle = None

                progress_bar = st.progress(0)
                status_area  = st.empty()
                log_area     = st.container()

                already_done = {r.get("اسم الماركة", "") for r in st.session_state.brands_results}

                for i, (idx, row) in enumerate(df_brands.iterrows()):
                    if st.session_state.brands_stop:
                        st.warning("⏹️ تم إيقاف المعالجة.")
                        break

                    brand_name = str(row.get("اسم الماركة", f"ماركة #{idx}"))
                    if brand_name in already_done:
                        continue

                    status_area.markdown(f"**⏳ جاري معالجة:** {brand_name} ({i+1}/{total_brands})")

                    prompt   = build_brand_prompt(row.to_dict())
                    response = call_claude(prompt, api_keys)

                    result_row = row.to_dict()

                    if response:
                        try:
                            # Extract JSON from response
                            json_match = re.search(r'\{.*\}', response, re.DOTALL)
                            if json_match:
                                parsed = json.loads(json_match.group())
                                result_row["وصف مختصر عن الماركة"]                            = parsed.get("short_description", row.get("وصف مختصر عن الماركة", ""))
                                result_row["(Page Title) عنوان صفحة العلامة التجارية"]       = parsed.get("page_title", row.get("(Page Title) عنوان صفحة العلامة التجارية", ""))
                                result_row["(SEO Page URL) رابط صفحة العلامة التجارية"]     = parsed.get("seo_url", row.get("(SEO Page URL) رابط صفحة العلامة التجارية", ""))
                                result_row["(Page Description) وصف صفحة العلامة التجارية"] = parsed.get("meta_description", row.get("(Page Description) وصف صفحة العلامة التجارية", ""))
                            with log_area:
                                st.markdown(f'<div class="success-row">✅ {brand_name}</div>', unsafe_allow_html=True)
                        except json.JSONDecodeError:
                            with log_area:
                                st.markdown(f'<div class="error-row">⚠️ {brand_name} (خطأ في JSON - تم تطهيره فقط)</div>', unsafe_allow_html=True)
                    else:
                        with log_area:
                            st.markdown(f'<div class="error-row">⚠️ {brand_name} (تم تطهيره فقط)</div>', unsafe_allow_html=True)

                    st.session_state.brands_results.append(result_row)
                    progress_bar.progress(min((i + 1) / total_brands, 1.0))
                    time.sleep(batch_delay)

                st.session_state.brands_running = False
                st.success(f"✅ اكتملت معالجة {len(st.session_state.brands_results)} ماركة!")

            # Download brands
            if st.session_state.brands_results:
                st.markdown("---")
                st.markdown("### 📥 تنزيل نتائج الماركات")

                brands_result_df = pd.DataFrame(st.session_state.brands_results)

                col_bl1, col_bl2 = st.columns(2)
                with col_bl1:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        brands_result_df.to_excel(writer, index=False, sheet_name="ماركات لكجري نيش")
                    st.download_button(
                        "⬇️ تنزيل Excel",
                        data=buf.getvalue(),
                        file_name="luxury_niche_brands.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                with col_bl2:
                    csv_buf = brands_result_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                    st.download_button(
                        "⬇️ تنزيل CSV",
                        data=csv_buf,
                        file_name="luxury_niche_brands.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

                if st.button("🗑️ مسح نتائج الماركات", type="secondary"):
                    st.session_state.brands_results = []
                    st.rerun()

        except Exception as e:
            st.error(f"❌ خطأ في قراءة الملف: {e}")


# ══════════════════════════════════════════════
# TAB 3 — INSTANT SANITIZE (NO AI)
# ══════════════════════════════════════════════
with tab_sanitize:
    st.markdown("## 🧹 تطهير فوري بدون AI")
    st.info("""
    هذا الخيار يطهّر الملف من كل ذكر لـ \"مهووس\" و\"mahwous\" **فوراً** بدون استخدام الـ AI.
    مثالي إذا لم يكن لديك مفتاح API أو تريد معالجة سريعة لكل 7,604 منتج دفعة واحدة.
    """)

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        st.markdown("#### منتجات (XLSX)")
        file_s_products = st.file_uploader("رفع ملف المنتجات", type=["xlsx"], key="sanitize_products")

        if file_s_products:
            df_sp = pd.read_excel(file_s_products, header=1)
            original_count = 0
            sanitized_count = 0
            report = []

            for col in df_sp.columns:
                if df_sp[col].dtype == object:
                    before = df_sp[col].astype(str).str.contains("مهووس|mahwous|Mahwous", case=False, na=False).sum()
                    df_sp[col] = df_sp[col].apply(lambda x: sanitize_text(x) if isinstance(x, str) else x)
                    if before > 0:
                        report.append(f"📌 **{col}**: {before} خلية مُطهَّرة")
                    sanitized_count += int(before)

            st.success(f"✅ تم تطهير {sanitized_count} خلية في {len(df_sp):,} منتج!")

            if report:
                with st.expander("📋 تقرير التطهير"):
                    for r in report:
                        st.markdown(r)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_sp.to_excel(writer, index=False, sheet_name="منتجات لكجري نيش")
            st.download_button(
                "⬇️ تنزيل المنتجات المُطهَّرة",
                data=buf.getvalue(),
                file_name="luxury_niche_products_sanitized.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )

    with col_s2:
        st.markdown("#### ماركات (CSV)")
        file_s_brands = st.file_uploader("رفع ملف الماركات", type=["csv"], key="sanitize_brands")

        if file_s_brands:
            df_sb = pd.read_csv(file_s_brands)
            sanitized_count_b = 0
            report_b = []

            for col in df_sb.columns:
                if df_sb[col].dtype == object:
                    before = df_sb[col].astype(str).str.contains("مهووس|mahwous|Mahwous", case=False, na=False).sum()
                    df_sb[col] = df_sb[col].apply(lambda x: sanitize_text(x) if isinstance(x, str) else x)
                    if before > 0:
                        report_b.append(f"📌 **{col}**: {before} خلية مُطهَّرة")
                    sanitized_count_b += int(before)

            st.success(f"✅ تم تطهير {sanitized_count_b} خلية في {len(df_sb)} ماركة!")

            if report_b:
                with st.expander("📋 تقرير التطهير"):
                    for r in report_b:
                        st.markdown(r)

            csv_buf = df_sb.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                "⬇️ تنزيل الماركات المُطهَّرة",
                data=csv_buf,
                file_name="luxury_niche_brands_sanitized.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary",
            )

    # Instant text sanitize
    st.markdown("---")
    st.markdown("#### 📝 تطهير نص مباشر")
    user_text = st.text_area("الصق نصاً لتطهيره", height=150, placeholder="ادخل النص هنا...")
    if user_text:
        clean = sanitize_text(user_text)
        st.text_area("النص بعد التطهير", value=clean, height=150)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align:center; color:#888; font-size:0.85rem; padding: 1rem;">
        ✨ <strong style="color:#e8c45a">لكجري نيش | Luxury Niche</strong> — محوّل الهوية التجارية<br>
        مبني بـ Python & Streamlit | يدعم Claude Opus 4.5
    </div>
    """, unsafe_allow_html=True)

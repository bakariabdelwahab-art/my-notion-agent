import streamlit as st # pyright: ignore[reportMissingImports]
import json
import os
from openai import OpenAI # type: ignore
from notion_client import Client # type: ignore
from notion_client.errors import APIResponseError # type: ignore

# إعدادات الصفحة
st.set_page_config(
    page_title="Notion Template Agent",
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="expanded"
)

# عنوان التطبيق
st.title("🎨 وكيل إنشاء قوالب Notion")
st.markdown("---")
st.markdown("قم بإدخال وصف تفصيلي للقالب الذي تريده، وسيقوم الوكيل بإنشاؤه مباشرة في Notion!")

# الشريط الجانبي للإعدادات
st.sidebar.header("⚙️ الإعدادات")
st.sidebar.markdown("### معلومات الاتصال بـ Notion")

# إدخال بيانات الاتصال
notion_token = st.sidebar.text_input(
    "رمز التكامل (Integration Token)",
    type="password",
    placeholder="ntn_...",
    help="يمكنك الحصول عليه من صفحة My Integrations في Notion"
)

parent_db_id = st.sidebar.text_input(
    "معرف قاعدة البيانات (Database ID)",
    placeholder="c4d14bc60529487fa7a6a85c7539d4e1",
    help="معرف قاعدة البيانات التي سيتم إنشاء القوالب بداخلها"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### معلومات إضافية")
st.sidebar.info(
    "**ملاحظة:** تأكد من مشاركة قاعدة البيانات مع التكامل قبل الاستخدام."
)

# الدالة الرئيسية لتوليد الحمولة
def generate_notion_payload(description: str, parent_id: str) -> dict:
    """
    يستخدم LLM لتحويل الوصف النصي إلى حمولة (Payload) صالحة لـ Notion API.
    """
    client = OpenAI()
    
    system_prompt = f"""
    أنت خبير في Notion API ومهمتك هي تحويل وصف نصي طبيعي ومفصل لقالب Notion إلى حمولة JSON صالحة
    لـ endpoint: POST /v1/pages.
    
    يجب أن تتضمن الحمولة الحقول التالية:
    1. "parent": يجب أن يكون نوعه "database_id" وقيمته هي {parent_id}.
    2. "properties": لتحديد خصائص قاعدة البيانات (مثل العنوان).
    3. "children": مصفوفة من كتل Notion (Blocks) التي تشكل محتوى القالب.
    
    يجب أن يكون الإخراج عبارة عن كائن JSON خام وصالح فقط، دون أي نص إضافي أو شرح.
    استخدم أنواع الكتل الشائعة مثل "heading_1", "paragraph", "to_do", "bulleted_list_item", "toggle", و "callout".
    
    ملاحظة هامة: يجب أن تكون عناصر "rich_text" من نوع "text" فقط.
    يجب استخدام "bulleted_list_item" لإنشاء عناصر القائمة النقطية.
    يجب استخدام "to_do" لإنشاء عناصر قائمة المهام.
    عند إنشاء كتل "callout"، تجنب تضمين حقل "icon" إذا لم يتم تحديد أيقونة صريحة، أو قم بتعيينه إلى أيقونة افتراضية صالحة.
    
    مثال على بنية الإخراج المطلوبة:
    {{
        "parent": {{
            "database_id": "{parent_id}"
        }},
        "properties": {{
            "Title": [
                {{
                    "text": {{
                        "content": "عنوان القالب"
                    }}
                }}
            ]
        }},
        "children": [
            {{
                "object": "block",
                "type": "heading_1",
                "heading_1": {{
                    "rich_text": [
                        {{
                            "text": {{
                                "content": "المحتوى"
                            }}
                        }}
                    ]
                }}
            }}
        ]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"الوصف التفصيلي للقالب: {description}"}
            ],
            response_format={"type": "json_object"}
        )
        
        json_string = response.choices[0].message.content.strip()
        payload = json.loads(json_string)
        return payload
        
    except Exception as e:
        raise Exception(f"خطأ في توليد الحمولة: {str(e)}")

# الدالة لإنشاء الصفحة
def create_notion_page(payload: dict, notion_token: str) -> str:
    """
    ينشئ صفحة Notion باستخدام الحمولة ورمز API المميز.
    """
    try:
        notion = Client(auth=notion_token)
        response = notion.pages.create(**payload)
        
        page_id = response["id"]
        clean_page_id = page_id.replace("-", "")
        page_url = f"https://www.notion.so/{clean_page_id}"
        
        return page_url
        
    except APIResponseError as e:
        raise Exception(f"خطأ في Notion API: {e.code} - {str(e)}")
    except Exception as e:
        raise Exception(f"خطأ غير متوقع: {str(e)}")

# المحتوى الرئيسي
st.markdown("### 📝 وصف القالب")
description = st.text_area(
    "أدخل وصفاً تفصيلياً للقالب الذي تريده:",
    height=150,
    placeholder="مثال: أريد قالبًا لإدارة المشاريع يحتوي على عنوان رئيسي 'خطة المشروع'، ثم قسم 'المهام' بقائمة مهام فارغة، وقسم 'ملاحظات' في كتلة تبديل...",
    label_visibility="collapsed"
)

st.markdown("---")

# زر الإنشاء
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    create_button = st.button("🚀 إنشاء القالب", use_container_width=True, type="primary")

# معالجة الضغط على الزر
if create_button:
    # التحقق من المدخلات
    if not notion_token:
        st.error("❌ يرجى إدخال رمز التكامل (Integration Token)")
    elif not parent_db_id:
        st.error("❌ يرجى إدخال معرف قاعدة البيانات (Database ID)")
    elif not description.strip():
        st.error("❌ يرجى إدخال وصف القالب")
    else:
        # بدء عملية الإنشاء
        with st.spinner("⏳ جاري إنشاء القالب..."):
            try:
                # توليد الحمولة
                st.info("🔄 جاري تحليل الوصف وتوليد الحمولة...")
                payload = generate_notion_payload(description, parent_db_id)
                
                # إنشاء الصفحة
                st.info("🔗 جاري الاتصال بـ Notion API وإنشاء الصفحة...")
                page_url = create_notion_page(payload, notion_token)
                
                # النجاح
                st.success("✅ تم إنشاء القالب بنجاح!")
                
                # عرض الرابط
                st.markdown("### 🎉 النتيجة")
                st.markdown(f"**رابط القالب:** [{page_url}]({page_url})")
                
                # نسخ الرابط
                st.code(page_url, language="text")
                
                # التعليمات التالية
                st.markdown("---")
                st.markdown("### 📋 الخطوة التالية (يدوية)")
                st.markdown("""
                1. افتح الرابط أعلاه في Notion.
                2. انقر على زر **"Share"** (مشاركة) في الزاوية العلوية اليمنى.
                3. قم بتفعيل خيار **"Share to web"** (مشاركة إلى الويب) للحصول على الرابط القابل للمشاركة.
                """)
                
            except Exception as e:
                st.error(f"❌ حدث خطأ: {str(e)}")

# تذييل الصفحة
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 12px;">
    <p>تم تطويره بواسطة Notion Template Agent | جميع الحقوق محفوظة © 2024</p>
</div>
""", unsafe_allow_html=True)

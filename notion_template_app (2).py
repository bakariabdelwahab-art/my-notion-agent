import streamlit as st
import json
import os
from openai import OpenAI # Groq يستخدم نفس مكتبة OpenAI
from notion_client import Client
from notion_client.errors import APIResponseError

# إعدادات الصفحة
st.set_page_config(
    page_title="Notion Template Agent (Groq Edition)",
    page_icon="⚡",
    layout="centered"
)

# عنوان التطبيق
st.title("⚡ وكيل Notion (نسخة Groq المجانية)")
st.markdown("---")

# الشريط الجانبي للإعدادات
st.sidebar.header("⚙️ الإعدادات")

# إدخال مفتاح Groq
groq_api_key = st.sidebar.text_input(
    "مفتاح Groq API",
    type="password",
    placeholder="gsk_...",
    help="احصل عليه مجاناً من console.groq.com"
)

# إدخال بيانات Notion
notion_token = st.sidebar.text_input(
    "رمز تكامل Notion",
    type="password",
    placeholder="ntn_..."
)

parent_db_id = st.sidebar.text_input(
    "معرف قاعدة بيانات Notion",
    placeholder="c4d14bc60529487fa7a6a85c7539d4e1"
)

# الدالة الرئيسية لتوليد الحمولة باستخدام Groq
def generate_notion_payload(description: str, parent_id: str, api_key: str) -> dict:
    # إعداد عميل Groq (متوافق مع OpenAI)
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key
    )
    
    system_prompt = f"""
    أنت خبير في Notion API. حول الوصف التالي إلى JSON صالح لـ POST /v1/pages.
    المتطلبات:
    1. "parent": {{"database_id": "{parent_id}"}}
    2. "properties": {{"Title": [{{"text": {{"content": "عنوان القالب"}}}}]}}
    3. "children": مصفوفة من الكتل (heading_1, paragraph, to_do, bulleted_list_item, callout).
    
    ملاحظات:
    - استخدم "Title" كاسم لخاصية العنوان.
    - استخدم "text" فقط داخل rich_text.
    - أخرج JSON خام فقط.
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # نموذج قوي ومجاني على Groq
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": description}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise Exception(f"خطأ في Groq: {str(e)}")

# دالة إنشاء الصفحة في Notion
def create_notion_page(payload: dict, token: str) -> str:
    try:
        notion = Client(auth=token)
        response = notion.pages.create(**payload)
        return f"https://www.notion.so/{response['id'].replace('-', '')}"
    except Exception as e:
        raise Exception(f"خطأ في Notion: {str(e)}")

# الواجهة الرئيسية
description = st.text_area("صف القالب الذي تريده بالتفصيل:", height=150)

if st.button("🚀 إنشاء القالب مجاناً", type="primary"):
    if not groq_api_key or not notion_token or not parent_db_id:
        st.error("⚠️ يرجى ملء جميع الإعدادات في الشريط الجانبي.")
    elif not description:
        st.error("⚠️ يرجى كتابة وصف للقالب.")
    else:
        with st.spinner("⏳ جاري العمل باستخدام Groq و Notion..."):
            try:
                payload = generate_notion_payload(description, parent_db_id, groq_api_key)
                url = create_notion_page(payload, notion_token)
                st.success("✅ تم الإنشاء بنجاح!")
                st.markdown(f"🔗 **رابط القالب:** [{url}]({url})")
                st.balloons()
            except Exception as e:
                st.error(f"❌ فشل: {str(e)}")

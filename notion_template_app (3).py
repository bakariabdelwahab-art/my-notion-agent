import streamlit as st
import json
from openai import OpenAI
from notion_client import Client

# إعدادات الصفحة
st.set_page_config(page_title="Notion Agent", page_icon="⚡")

st.title("⚡ وكيل Notion الذكي")
st.markdown("أنشئ قوالب Notion احترافية باستخدام الذكاء الاصطناعي (Groq)")

# الإعدادات في الشريط الجانبي
with st.sidebar:
    st.header("⚙️ الإعدادات")
    groq_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    notion_token = st.text_input("Notion Token", type="password", placeholder="ntn_...")
    database_id = st.text_input("Database ID", placeholder="32 حرف ورقم")
    
    st.info("تأكد من مشاركة قاعدة البيانات مع التكامل في Notion.")

# دالة توليد القالب
def generate_template(desc, g_key, db_id):
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=g_key)
    
    prompt = f"تحويل الوصف التالي إلى JSON لـ Notion API (POST /v1/pages). القاعدة: {db_id}. الوصف: {desc}. أخرج JSON فقط."
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# الواجهة الرئيسية
user_input = st.text_area("صف القالب الذي تريده:", height=150)

if st.button("🚀 إنشاء القالب", type="primary"):
    if not all([groq_key, notion_token, database_id, user_input]):
        st.error("⚠️ يرجى ملء جميع الحقول.")
    else:
        try:
            with st.spinner("جاري المعالجة..."):
                # 1. توليد الحمولة
                payload = generate_template(user_input, groq_key, database_id)
                
                # 2. الإرسال لـ Notion
                notion = Client(auth=notion_token)
                res = notion.pages.create(**payload)
                
                url = f"https://www.notion.so/{res['id'].replace('-', '')}"
                st.success("✅ تم إنشاء القالب!")
                st.markdown(f"🔗 [اضغط هنا لفتح القالب]({url})")
        except Exception as e:
            st.error(f"❌ حدث خطأ: {str(e)}")

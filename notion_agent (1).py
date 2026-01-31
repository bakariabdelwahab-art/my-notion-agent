import os
import json
from openai import OpenAI
from notion_client import Client
from notion_client.errors import APIResponseError

# يجب أن يكون هذا هو معرف الصفحة/قاعدة البيانات التي سيتم إنشاء القوالب بداخلها
# سيتم طلب هذا من المستخدم لاحقًا
PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_ID")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")

def generate_notion_payload(description: str) -> dict:
    """
    يستخدم LLM لتحويل الوصف النصي إلى حمولة (Payload) صالحة لـ Notion API.
    """
    print("-> جاري تحليل الوصف وإنشاء حمولة Notion API...")
    
    client = OpenAI()
    
    # التعليمات التفصيلية للنموذج لضمان إخراج JSON صحيح
    system_prompt = f"""
    أنت خبير في Notion API ومهمتك هي تحويل وصف نصي طبيعي ومفصل لقالب Notion إلى حمولة JSON صالحة
    لـ endpoint: POST /v1/pages.
    
    يجب أن تتضمن الحمولة الحقول التالية:
    1. "parent": يجب أن يكون نوعه "database_id" وقيمته هي {PARENT_PAGE_ID}.
    2. "properties": لتحديد خصائص قاعدة البيانات (مثل العنوان).
    3. "children": مصفوفة من كتل Notion (Blocks) التي تشكل محتوى القالب.
    
    يجب أن يكون الإخراج عبارة عن كائن JSON خام وصالح فقط، دون أي نص إضافي أو شرح.
    استخدم أنواع الكتل الشائعة مثل "heading_1", "paragraph", "to_do", "bulleted_list", "toggle", و "callout".
    
    ملاحظة هامة: يجب أن تكون عناصر "rich_text" من نوع "text" فقط، ولا تستخدم أي أنواع أخرى مثل "date" أو "mention" أو "equation" إلا إذا كنت متأكدًا من صحة تركيبها. لتجنب الأخطاء، استخدم "text" فقط.
    
    يجب استخدام "bulleted_list_item" لإنشاء عناصر القائمة النقطية، وليس "bulleted_list".
    يجب استخدام "to_do" لإنشاء عناصر قائمة المهام.
    
    ملاحظة إضافية: عند إنشاء كتل "callout"، يجب **تجنب** تضمين حقل "icon" إذا لم يتم تحديد أيقونة صريحة في الوصف، أو قم بتعيينه إلى أيقونة افتراضية صالحة (مثل رمز تعبيري) بدلاً من "null".
    
    مثال على بنية الإخراج المطلوبة:
    {{
        "parent": {{
            "database_id": "{PARENT_PAGE_ID}"
        }},
        "properties": {{
            "Title": [
                {{
                    "text": {{
                        "content": "عنوان القالب المقترح"
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
                                "content": "مقدمة القالب"
                            }}
                        }}
                    ]
                }}
            }},
            {{
                "object": "block",
                "type": "paragraph",
                "paragraph": {{
                    "rich_text": [
                        {{
                            "text": {{
                                "content": "هذا القالب تم إنشاؤه بواسطة الوكيل."
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
            model="gpt-4.1-mini", # استخدام نموذج قادر على اتباع التعليمات بدقة
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"الوصف التفصيلي للقالب: {description}"}
            ],
            response_format={"type": "json_object"}
        )
        
        # التأكد من أن الاستجابة هي JSON
        json_string = response.choices[0].message.content.strip()
        payload = json.loads(json_string)
        return payload
        
    except Exception as e:
        print(f"خطأ في توليد الحمولة: {e}")
        print("يرجى مراجعة سجلات LLM للحصول على تفاصيل.")
        return None

def create_notion_page(payload: dict, notion_token: str) -> str | None:
    """
    ينشئ صفحة Notion باستخدام الحمولة (Payload) ورمز API المميز.
    """
    print("-> جاري الاتصال بـ Notion API وإنشاء الصفحة...")
    
    try:
        notion = Client(auth=notion_token)
        
        # استخدام pages.create لإنشاء الصفحة والمحتوى (الأطفال)
        response = notion.pages.create(**payload)
        
        page_id = response["id"]
        # Notion URLs تستخدم صيغة بدون فواصل في الـ UUID
        clean_page_id = page_id.replace("-", "")
        
        # بناء الرابط الداخلي للصفحة
        page_url = f"https://www.notion.so/{clean_page_id}"
        
        return page_url
        
    except APIResponseError as e:
        # إصلاح معالجة الخطأ
        print(f"خطأ في Notion API (الحالة: {e.status}): {e.code}")
        print(f"رسالة الخطأ التفصيلية: {e}")
        return None
    except Exception as e:
        print(f"خطأ غير متوقع أثناء إنشاء الصفحة: {e}")
        return None

import sys

def main(description: str):
    """
    وظيفة رئيسية لتنسيق عملية إنشاء القالب.
    """
    if not NOTION_TOKEN or not PARENT_PAGE_ID:
        print("خطأ: لم يتم تعيين متغيرات البيئة NOTION_TOKEN أو NOTION_PARENT_ID.")
        print("يرجى تزويد الوكيل برمز التكامل (Integration Token) ومعرف الصفحة الأم (Parent Page ID).")
        return None

    # 1. توليد الحمولة
    payload = generate_notion_payload(description)
    
    if not payload:
        print("فشل في توليد حمولة صالحة. توقف.")
        return None

    print("\n--- الحمولة المولدة (للتصحيح) ---")
    print(json.dumps(payload, indent=2))
    print("----------------------------------\n")

    # 2. إنشاء الصفحة
    page_url = create_notion_page(payload, NOTION_TOKEN)
    
    if page_url:
        print("\n--- نجاح ---")
        print(f"تم إنشاء القالب بنجاح في Notion.")
        print(f"الرابط الداخلي للقالب: {page_url}")
        print("\nالخطوة التالية (يدوية):")
        print("1. افتح الرابط أعلاه.")
        print("2. انقر على زر 'مشاركة' (Share) في الزاوية العلوية اليمنى.")
        print("3. قم بتفعيل خيار 'مشاركة إلى الويب' (Share to web) للحصول على الرابط القابل للمشاركة.")
        return page_url
    else:
        print("\n--- فشل ---")
        print("فشل في إنشاء القالب عبر Notion API.")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("الاستخدام: python3 notion_agent.py \"وصف القالب\"")
        sys.exit(1)
    
    description = sys.argv[1]
    main(description)

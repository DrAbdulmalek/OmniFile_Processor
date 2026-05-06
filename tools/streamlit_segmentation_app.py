import streamlit as st
import cv2
import numpy as np
from pdf2image import convert_from_bytes
from PIL import Image

st.set_page_config(layout="wide")
st.title("تطبيق OCR تفاعلي لملاحظات بايثون 📝")
st.write("قم برفع ملف الـ PDF الخاص بملاحظاتك لتقسيمها وتجهيزها للتدريب.")

# 1. رفع الملف
uploaded_file = st.file_uploader("اختر ملف PDF لملاحظاتك", type=["pdf"])

if uploaded_file is not None:
    # تحويل PDF إلى صور
    images = convert_from_bytes(uploaded_file.read())
    
    # اختيار رقم الصفحة
    page_num = st.sidebar.slider("اختر رقم الصفحة", 1, len(images), 1)
    img = np.array(images[page_num - 1])
    
    # تحويل الصورة إلى تدرج الرمادي
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # إعدادات تفاعلية في الشريط الجانبي
    st.sidebar.header("إعدادات المعالجة والتقسيم")
    threshold_val = st.sidebar.slider("قيمة Threshold (التحكم في العزل)", 50, 255, 127)
    kernel_x = st.sidebar.slider("تمدد الكلمات أفقيًا (Kernel X)", 1, 50, 15)
    kernel_y = st.sidebar.slider("تمدد الكلمات عموديًا (Kernel Y)", 1, 50, 5)

    # 2. معالجة الصورة (Binarization)
    _, binary = cv2.threshold(gray, threshold_val, 255, cv2.THRESH_BINARY_INV)
    
    # 3. تجميع الحروف لتكوين كلمات
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_x, kernel_y))
    dilated = cv2.dilate(binary, kernel, iterations=1)
    
    # 4. إيجاد الكنتورات (الحدود) لتحديد الكلمات
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # رسم المربعات على الصورة الأصلية للكلمات
    img_words = img.copy()
    words_data = []
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 10 and h > 10:  # تصفية النقاط الصغيرة جداً
            cv2.rectangle(img_words, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # قص الكلمة لحفظها لاحقاً
            word_crop = binary[y:y+h, x:x+w]
            words_data.append(word_crop)
            
    # عرض النتائج في التطبيق
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("الصورة المحددة (الكلمات)")
        st.image(img_words, use_container_width=True)
        
    with col2:
        st.subheader("قناع المعالجة الثنائي (Binary)")
        st.image(dilated, use_container_width=True)

    st.success(f"تم اكتشاف {len(contours)} كلمة أو سطر في هذه الصفحة!")
    
    # عرض عينات للكلمات المقصوصة
    st.subheader("معاينة لبعض الكلمات المقصوصة لتدريب الـ OCR:")
    cols = st.columns(6)
    for i, word in enumerate(words_data[:12]): # عرض أول 12 كلمة فقط كمثال
        with cols[i % 6]:
            st.image(word, caption=f"قصة {i+1}")
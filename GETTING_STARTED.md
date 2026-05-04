# 🚀 البدء السريع — OmniFile AI Processor

## التثبيت (دقيقتان)

```bash
git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
cd OmniFile_Processor
bash scripts/setup.sh
```

## التشغيل

```bash
python -m src.gradio_ui        # واجهة Gradio (7 تبويبات)
streamlit run app.py           # واجهة Streamlit
python process.py -i img.jpg -o out -e surya --correct --export-docx
```

## على Google Colab

```python
!git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
%cd OmniFile_Processor
!pip install -r requirements-colab.txt
```

ثم افتح `notebooks/OmniFile_Diagnostic.ipynb`

## على الجوال

```bash
python mobile_review/server.py --host 0.0.0.0 --port 5000
# افتح من الهاتف: http://<IP>:5000
```

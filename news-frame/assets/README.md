# ضع الشعار هنا

ضع ملف الشعار الأصلي في هذا المجلد باسم:

```
news-frame/assets/logo.png
```

يفضّل أن يكون PNG بخلفية شفافة. (إن كان JPG، سيزيل السكربت الخلفية البيضاء المحيطة تلقائيًا.)

ثم نفّذ أمرًا واحدًا فقط:

```bash
cd news-frame
python3 -m venv .venv && .venv/bin/pip install Pillow numpy
.venv/bin/python build_frame.py --logo assets/logo.png --outdir output
.venv/bin/python make_preview.py --frame output/SignatureFrame_1080x1920.png \
                                 --photo preview/_sample_photo_for_preview.jpg --outdir preview
```

النتيجة:
- `output/SignatureFrame_1080x1920.png` — الملف النهائي 1080×1920 بشفافية حقيقية
- `output/report.json` — تقرير الفحص (الشفافية، المقاس، ألوان الشعار المستخرجة، التداخل مع واجهة TikTok)

الشعار يُستخدم كما هو: نفس الحروف، نفس النسب، نفس الألوان — بلا إعادة رسم ولا تحرير ولا تشويه.

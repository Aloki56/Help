#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIGNATURE FRAME SYSTEM
======================
بناء إطار إعلامي (News Media Overlay Frame) بدقة 1080x1920 بنسبة 9:16،
بقناة Alpha حقيقية (RGBA) ليُستخدم كطبقة Overlay فوق الصور والفيديو في TikTok.

المكوّنات: الإطار الهندسي + الشعار الأصلي فقط. لا نصوص، لا أيقونات، لا علامات مائية.

الاستخدام:
    python3 build_frame.py --logo path/to/logo.png --outdir output

المخرجات:
    SignatureFrame_1080x1920.png      الملف النهائي بشفافية حقيقية
    SignatureFrame_topzone.png        نسخة المنطقة العلوية فقط (للمقاطع التي لا تحتمل إطارًا كاملًا)
    report.json                        تقرير فحص آلي (الشفافية، المقاس، مناطق واجهة TikTok)
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

# ----------------------------------------------------------------------------------
# 1) المقاس المستهدف
# ----------------------------------------------------------------------------------
W, H = 1080, 1920                 # 9:16 عمودي - TikTok

# عامل الرسم الفائق (Supersampling): نرسم بأضعاف المقاس ثم نُصغّر لتنعيم الحواف بلا تعرّجات
SS = 3

# ----------------------------------------------------------------------------------
# 2) هندسة الإطار — "نافذة الحدث" بخطوط متقطعة محسوبة
#    الإحداثيات بوحدة البكسل على مقاس 1080x1920، والنقطة (0,0) أعلى اليسار
# ----------------------------------------------------------------------------------
BOX_L, BOX_R = 64, 1016           # الحافتان الرأسيتان للنافذة (متماثلتان حول المركز 540)
BOX_T, BOX_B = 214, 1400          # الأعلى: تحت واجهة TikTok العلوية — الأسفل: فوق القرص والوصف

LINE = 3                          # سماكة الخطوط الرفيعة
KEEPER = 1                        # هالة داكنة بسماكة 1px حول كل خط لضمان الظهور فوق أي خلفية
ARM = 132                         # طول ذراع الزاوية
CHAMFER = 28                      # القطع المائل 45° عند رأس الزاوية (وحدة الهوية المتكررة)

# المقاطع الوسطية فقط — أذرع الزوايا تُحسب تلقائيًا معها
TOP_SEGS    = [(250, 390), (452, 628), (690, 830)]     # الحافة العلوية y = BOX_T
BOTTOM_SEGS = [(470, 610)]                             # الحافة السفلية y = BOX_B
LEFT_SEGS   = [(560, 960)]                             # الحافة اليسرى x = BOX_L
RIGHT_SEGS  = []                                       # الحافة اليمنى: الأذرع فقط (احترامًا لأزرار TikTok)

# ----------------------------------------------------------------------------------
# 3) عنصر البصمة (Signature Notch): شريط أحمر قصير بنهايات مائلة 45° — الوحدة نفسها في كل الإطار
# ----------------------------------------------------------------------------------
NOTCH = dict(len=36, thick=10, shear=10)               # shear = thick ⇒ نهايات بزاوية 45°
NOTCHES = [
    ("v", BOX_L, 1090),           # يسار: علامة قياس في منتصف الانقطاع
    ("h", 248, BOX_B),            # أسفل يسار
    ("h", 664, BOX_B),            # أسفل يمين (إيقاع مقصود غير متماثل)
]

# ----------------------------------------------------------------------------------
# 4) حاضنة الشعار (Logo Chamber): لوحة هندسية شفافة جزئيًا، ملتحمة بمحور الإطار الأيمن
#    تُقاس تلقائيًا على مقاس الشعار الأصلي مع وحدة القطع المائل نفسها (CHAMFER)
# ----------------------------------------------------------------------------------
PLATE = dict(top=16, pad_v=16, pad_l=30, pad_r=28, red_bar=5)
LOGO_MAX_H = 74
LOGO_MAX_W = 380

# ----------------------------------------------------------------------------------
# 5) الألوان — تُستخرج من الشعار نفسه، مع بدائل مؤسسية رصينة
# ----------------------------------------------------------------------------------
FALLBACK = {
    "red":  (168, 24, 43),        # أحمر داكن
    "ink":  (10, 11, 14),         # أسود مطفأ
    "char": (22, 24, 29),         # فحمي
    "light": (255, 255, 255),     # أبيض
}
ALPHA_LINE = 232
ALPHA_KEEPER = 120
ALPHA_PLATE = 176                 # شفافية جزئية خلف الشعار فقط

# ----------------------------------------------------------------------------------
# 6) مناطق واجهة TikTok التقريبية (للفحص الآلي فقط)
# ----------------------------------------------------------------------------------
TIKTOK_UI = {
    "top_tabs":   (300, 118, 790, 205),
    "search":     (980, 125, 1065, 200),
    "right_rail": (945, 470, 1065, 1130),
    "music_disc": (945, 1440, 1065, 1630),
    "caption":    (0, 1660, 770, 1880),
    "bottom_nav": (0, 1830, 1080, 1920),
}
SAFE_LOGO = (40, 0, 1040, 210)    # المنطقة الآمنة للشعار


# ==================================================================================
# أدوات الرسم
# ==================================================================================
def s(v):
    """تحويل إحداثي من مقاس 1080x1920 إلى مقاس الرسم الفائق"""
    return int(round(v * SS))


def darken(rgb, k=0.72):
    return tuple(int(round(c * k)) for c in rgb)


def stroke(draw, xy, width, color, alpha, keeper=True):
    """رسم خط مع هالة داكنة خفيفة تحته لضمان التباين على أي خلفية"""
    if keeper:
        draw.line(xy, fill=color["ink"] + (ALPHA_KEEPER,), width=s(width + 2 * KEEPER), joint="curve")
    draw.line(xy, fill=color["light"] + (alpha,), width=s(width), joint="curve")


def fill_poly(draw, pts, color, alpha, keeper=True):
    if keeper:
        draw.polygon(pts, fill=color["ink"] + (ALPHA_KEEPER,))
    draw.polygon(pts, fill=color["red"] + (alpha,))


def notch_poly(kind, a, b):
    """إرجاع مضلع عنصر البصمة (شريط مائل النهايتين)"""
    L, T, SH = NOTCH["len"], NOTCH["thick"], NOTCH["shear"]
    if kind == "v":                       # محور رأسي عند x=a يبدأ من y=b
        x, y = a, b
        return [(s(x - T / 2), s(y + SH)), (s(x + T / 2), s(y)),
                (s(x + T / 2), s(y + L)), (s(x - T / 2), s(y + L + SH))]
    x, y = a, b                           # محور أفقي عند y=b يبدأ من x=a
    return [(s(x), s(y - T / 2)), (s(x + L), s(y - T / 2)),
            (s(x + L + SH), s(y + T / 2)), (s(x + SH), s(y + T / 2))]


# ==================================================================================
# تحليل الشعار واستخراج ألوانه
# ==================================================================================
def extract_palette(logo, k=8, seed=0):
    """تحليل ألوان الشعار بطريقة k-means لإرجاع: الأحمر، الأسود، الفحمي، الفاتح"""
    rgba = np.asarray(logo.convert("RGBA"), dtype=np.float32)
    a = rgba[..., 3]
    px = rgba[..., :3][a > 140]
    if px.size == 0:
        px = rgba[..., :3].reshape(-1, 3)
    px = px / 255.0
    if len(px) > 30000:
        rng = np.random.default_rng(seed)
        px = px[rng.choice(len(px), 30000, replace=False)]

    # تهيئة المراكز
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(px), k, replace=False)
    C = px[idx].copy()
    for _ in range(40):
        d = ((px[:, None, :] - C[None, :, :]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            m = lab == j
            if m.sum():
                C[j] = px[m].mean(0)
    # حساب الثقل والخصائص اللونية لكل عنقود
    d = ((px[:, None, :] - C[None, :, :]) ** 2).sum(-1)
    lab = d.argmin(1)
    clusters = []
    for j in range(k):
        m = lab == j
        if m.sum() < max(8, 0.002 * len(px)):
            continue
        c = C[j]
        r, g, b = c
        mx, mn = c.max(), c.min()
        sat = 0.0 if mx == 0 else (mx - mn) / mx
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        # زاوية اللون (Hue)
        if mx == mn:
            hue = 0.0
        elif mx == r:
            hue = (60 * ((g - b) / (mx - mn)) + 360) % 360
        elif mx == g:
            hue = 60 * ((b - r) / (mx - mn)) + 120
        else:
            hue = 60 * ((r - g) / (mx - mn)) + 240
        clusters.append(dict(rgb=(int(round(r * 255)), int(round(g * 255)), int(round(b * 255))),
                             weight=float(m.mean()), lum=float(lum), sat=float(sat), hue=float(hue)))

    pal = dict(FALLBACK)
    if clusters:
        # الأحمر: عنقود مشبع ضمن نطاق الأحمر، وإلا أكثر العناقيد إشباعًا
        reds = [c for c in clusters if c["sat"] > 0.30 and (c["hue"] <= 22 or c["hue"] >= 335)]
        reds.sort(key=lambda c: -c["weight"] * (c["sat"] + 0.3))
        if reds:
            pal["red"] = reds[0]["rgb"]
        else:
            chroma = sorted(clusters, key=lambda c: -c["sat"])
            if chroma and chroma[0]["sat"] > 0.22:
                pal["red"] = chroma[0]["rgb"]
        # الفاتح
        lights = [c for c in clusters if c["lum"] > 0.80 and c["sat"] < 0.18]
        if lights:
            pal["light"] = max(lights, key=lambda c: c["weight"])["rgb"]
        # الأسود/الفحمي
        darks = [c for c in clusters if c["lum"] < 0.16]
        if darks:
            pal["ink"] = min(darks, key=lambda c: c["lum"])["rgb"]
        mids = [c for c in clusters if 0.16 <= c["lum"] < 0.42]
        if mids:
            pal["char"] = min(mids, key=lambda c: abs(c["lum"] - 0.26))["rgb"]

    # توحيد رصانة الأحمر: نغمته يجب أن تبقى داكنة/مؤسسية
    r, g, b = pal["red"]
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    if lum > 0.42:
        pal["red"] = darken(pal["red"], 0.42 / max(lum, 1e-6))
    if lum < 0.10:
        pal["red"] = tuple(int(round(min(255, c / max(lum, 1e-6) * 0.16))) for c in pal["red"])
    return pal, clusters


# ==================================================================================
# تحجيم آمن للشعار مع الحفاظ على النسب (بدون تشويه)
# ==================================================================================
def load_logo(path):
    """تحميل الشعار كما هو. إن كان بلا شفافية (JPG مثلًا) تُزاح خلفيته البيضاء فقط."""
    im = Image.open(path)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        return im.convert("RGBA"), False
    im = im.convert("RGB")
    arr = np.asarray(im, np.float32) / 255.0
    border = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])
    lum_b = float((border @ np.array([0.2126, 0.7152, 0.0722], np.float32)).mean())
    if lum_b < 0.90:                       # خلفية ليست بيضاء ⇒ لا نعبث بالصورة
        return im.convert("RGBA"), False
    lum = arr @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    a = np.clip((0.96 - lum) / 0.30, 0.0, 1.0)
    out = np.dstack([arr * 255.0, a * 255.0]).astype(np.uint8)
    return Image.fromarray(out, "RGBA"), True


def fit_logo(logo, max_w, max_h):
    """قصّ الشعار على حدوده الحقيقية ثم تصغيره مع الحفاظ على النسبة تمامًا"""
    logo = logo.convert("RGBA")
    bbox = logo.getbbox()                     # الحدود الفعلية للمحتوى غير الشفاف
    if bbox:
        logo = logo.crop(bbox)
    w, h = logo.size
    k = min(max_w / float(w), max_h / float(h))
    nw, nh = max(1, int(round(w * k))), max(1, int(round(h * k)))
    return logo, (nw, nh)


def resize_rgba_safe(img, size):
    """تصغير RGBA بضرب مسبق للألفا (Premultiplied) لتفادي الهالات الداكنة على الحواف"""
    arr = np.asarray(img, dtype=np.float32)
    al = arr[..., 3:4] / 255.0
    pm = np.clip(arr[..., :3] * al, 0, 255).astype(np.uint8)
    pm2 = Image.fromarray(pm, "RGB").resize(size, Image.LANCZOS, reducing_gap=3.0)
    a2 = img.getchannel("A").resize(size, Image.LANCZOS, reducing_gap=3.0)
    out = np.zeros((size[1], size[0], 4), np.float32)
    out[..., :3] = np.asarray(pm2, np.float32)
    out[..., 3] = np.asarray(a2, np.float32)
    a3 = out[..., 3:4] / 255.0
    out[..., :3] = np.where(a3 > 0, out[..., :3] / np.maximum(a3, 1e-6), 0.0)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


# ==================================================================================
# بناء الإطار
# ==================================================================================
def build(logo_path, color, with_bottom=True, top_only=False, no_logo=False):
    canvas = Image.new("RGBA", (s(W), s(H)), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)

    # ---------- حاضنة الشعار: لوحة هندسية تقيس نفسها على الشعار الأصلي ----------
    plate_box = None
    if not no_logo:
        logo_src, keyed = load_logo(logo_path)
        logo, (lw, lh) = fit_logo(logo_src, LOGO_MAX_W, LOGO_MAX_H)
        pw = lw + PLATE["pad_l"] + PLATE["pad_r"] + PLATE["red_bar"]
        ph = lh + 2 * PLATE["pad_v"]
        x1 = BOX_R
        x0 = x1 - pw
        y0 = PLATE["top"]
        y1 = y0 + ph
        # مضلع اللوحة: قطع مائل 45° (الوحدة نفسها) في الزاوية السفلية اليسرى
        d.polygon([(s(x0), s(y0)), (s(x1), s(y0)), (s(x1), s(y1)),
                   (s(x0 + CHAMFER), s(y1)), (s(x0), s(y1 - CHAMFER))],
                  fill=color["ink"] + (ALPHA_PLATE,))
        # شريط البداية الأحمر على حافة القراءة (يمين)
        d.rectangle([s(x1 - PLATE["red_bar"]), s(y0), s(x1), s(y1)], fill=color["red"] + (255,))
        # خط رفيع أسفل اللوحة يربطها ببنية الإطار
        d.rectangle([s(x0 + CHAMFER), s(y1 - 2), s(x1), s(y1)], fill=color["light"] + (150,))
        # الشعار الأصلي كما هو (نسبه محفوظة تمامًا)
        logo_hi = resize_rgba_safe(logo, (s(lw), s(lh)))
        lx = s(x1 - PLATE["red_bar"] - PLATE["pad_r"] - lw)
        ly = s((y0 + y1) / 2.0) - s(lh) // 2
        canvas.alpha_composite(logo_hi, (lx, ly))
        plate_box = (x0, y0, x1, y1)

    # ---------- زوايا الإطار (قطع مائل 45°) ----------
    def corner(px, py, sx, sy):
        pts = [(px, py + sy * ARM), (px, py + sy * CHAMFER),
               (px + sx * CHAMFER, py), (px + sx * ARM, py)]
        stroke(d, [(s(a), s(b)) for a, b in pts], LINE, color, ALPHA_LINE)

    corner(BOX_L, BOX_T, 1, 1)
    corner(BOX_R, BOX_T, -1, 1)
    if not top_only:
        corner(BOX_L, BOX_B, 1, -1)
        corner(BOX_R, BOX_B, -1, -1)

    # ---------- خطوط الحواف ----------
    for a, b in TOP_SEGS:
        stroke(d, [(s(a), s(BOX_T)), (s(b), s(BOX_T))], LINE, color, ALPHA_LINE)
    if not top_only:
        for a, b in LEFT_SEGS:
            stroke(d, [(s(BOX_L), s(a)), (s(BOX_L), s(b))], LINE, color, ALPHA_LINE)
        for a, b in RIGHT_SEGS:
            stroke(d, [(s(BOX_R), s(a)), (s(BOX_R), s(b))], LINE, color, ALPHA_LINE)
        if with_bottom:
            for a, b in BOTTOM_SEGS:
                stroke(d, [(s(a), s(BOX_B)), (s(b), s(BOX_B))], LINE, color, ALPHA_LINE)
    else:
        # نسخة المنطقة العلوية: أذرع قصيرة فقط أسفل الزاويتين
        for a, b in [(BOX_T + CHAMFER, BOX_T + ARM)]:
            stroke(d, [(s(BOX_L), s(a)), (s(BOX_L), s(b))], LINE, color, ALPHA_LINE)
            stroke(d, [(s(BOX_R), s(a)), (s(BOX_R), s(b))], LINE, color, ALPHA_LINE)

    # ---------- عنصر البصمة (أشرطة حمراء مائلة) ----------
    for kind, a, b in NOTCHES:
        if top_only and kind == "v":
            continue
        if b == BOX_B and not (with_bottom and not top_only):
            continue
        poly = notch_poly(kind, a, b)
        d.polygon(poly, fill=color["red"] + (255,))
        d.polygon(poly, outline=color["ink"] + (95,), width=1)

    return resize_rgba_safe(canvas, (W, H)), plate_box


# ==================================================================================
# فحص الجودة الآلي
# ==================================================================================
def verify(img, logo_path, color):
    arr = np.asarray(img)
    rep = {
        "size": [img.width, img.height],
        "mode": img.mode,
        "aspect": round(img.width / img.height, 4),
    }
    # الشفافية
    a = arr[..., 3]
    rep["transparent_pixel_percent"] = round(100.0 * float((a == 0).mean()), 3)
    interior = arr[300:1350, 210:870, 3]
    rep["interior_max_alpha"] = int(interior.max())
    rep["interior_fully_transparent"] = bool(interior.max() == 0)
    # بكسلات الشعار/الإطار
    rep["ink_pixel_percent"] = round(100.0 * float((a > 8).mean()), 3)
    # تداخل مع واجهة TikTok
    ui = {}
    for name, (x0, y0, x1, y1) in TIKTOK_UI.items():
        sub = a[y0:y1, x0:x1]
        ui[name] = {"ink_pixels": int((sub > 8).sum()),
                    "percent_of_zone": round(100.0 * float((sub > 8).mean()), 3)}
    rep["tiktok_ui_overlap"] = ui
    # الشعار
    if logo_path and os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        rep["logo_original_size"] = list(logo.size)
        rep["logo_aspect_ratio_original"] = round(logo.width / logo.height, 4)
    else:
        rep["logo_original_size"] = None
        rep["logo_aspect_ratio_original"] = None
    rep["palette"] = {k: list(v) for k, v in color.items()}
    rep["palette_hex"] = {k: "#%02X%02X%02X" % v for k, v in color.items()}
    return rep


# ==================================================================================
def main():
    global SS
    ap = argparse.ArgumentParser()
    ap.add_argument("--logo", required=True)
    ap.add_argument("--outdir", default="output")
    ap.add_argument("--ss", type=int, default=SS)
    ap.add_argument("--name", default="SignatureFrame")
    ap.add_argument("--no-logo", action="store_true")
    a = ap.parse_args()

    SS = a.ss
    os.makedirs(a.outdir, exist_ok=True)

    if a.no_logo:
        color, clusters = dict(FALLBACK), []
    else:
        color, clusters = extract_palette(Image.open(a.logo))
    print("Palette:", {k: "#%02X%02X%02X" % v for k, v in color.items()})

    variants = {
        "": dict(),
        "_topzone": dict(top_only=True),
        "_nobottom": dict(with_bottom=False),
    }
    rep = None
    for suffix, kw in variants.items():
        img, plate = build(a.logo, color, no_logo=a.no_logo, **kw)
        if suffix == "":
            rep_plate = plate
        out = os.path.join(a.outdir, f"{a.name}{suffix}_1080x1920.png")
        img.save(out, "PNG", optimize=True)
        print("saved:", out, img.size, img.mode)
        if suffix == "":
            rep = verify(img, (None if a.no_logo else a.logo), color)

    rep["logo_plate_box"] = list(rep_plate) if rep_plate else None
    rep["clusters"] = [
        {"rgb": c["rgb"], "weight": round(c["weight"], 4), "lum": round(c["lum"], 3),
         "sat": round(c["sat"], 3), "hue": round(c["hue"], 1)} for c in clusters
    ]
    with open(os.path.join(a.outdir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in rep.items() if k != "clusters"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())

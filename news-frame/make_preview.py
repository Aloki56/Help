#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أداة معاينة فقط (ليست من المخرجات النهائية):
تركّب الإطار الشفاف فوق خلفيات مختلفة (فاتحة / داكنة / ملونة / مربعات الشفافية)
وتخرج لوحة معاينة واحدة للتحقق من الوضوح والتباين، إضافة إلى صور منفصلة.
"""

import argparse
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def checker(size, cell=24):
    w, h = size
    a = np.indices((h, w)).sum(0) // cell
    v = np.where(a % 2 == 0, 225, 195).astype(np.uint8)
    return Image.fromarray(np.stack([v, v, v], -1), "RGB")


def light_bg(size):
    w, h = size
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    r = 245 - 30 * y - 10 * x
    g = 243 - 26 * y - 6 * x
    b = 238 - 22 * y
    return Image.fromarray(np.clip(np.stack([r + 0 * x, g + 0 * x, b + 0 * x], -1), 0, 255).astype(np.uint8), "RGB")


def dark_bg(size):
    w, h = size
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None] * np.ones((1, w), dtype=np.float32)
    v = 18 + 26 * y
    arr = np.stack([v, v + 2, v + 6], -1)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def busy_bg(size, rng):
    """خلفية مزدحمة التفاصيل لمحاكاة صورة ميدانية"""
    img = Image.new("RGB", size, (120, 118, 112))
    d = ImageDraw.Draw(img)
    for _ in range(1400):
        x = rng.integers(0, size[0]); y = rng.integers(0, size[1])
        r = int(rng.integers(4, 60))
        c = tuple(int(v) for v in rng.integers(20, 240, 3))
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)
    img = img.filter(ImageFilter.GaussianBlur(1.2))
    return img


def tiktok_ui(size):
    """رسم تقريبي لواجهة TikTok فوق المعاينة للتحقق من عدم التداخل"""
    w, h = size
    ov = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # تبويبات أعلى
    d.text((w // 2 - 70, 130), "Following | For You", fill=(255, 255, 255, 210))
    # بحث
    d.ellipse([w - 70, 130, w - 26, 174], outline=(255, 255, 255, 210), width=3)
    # الشريط الأيمن
    cx = w - 55
    for i, y in enumerate([520, 690, 850, 1000, 1150]):
        d.ellipse([cx - 24, y - 24, cx + 24, y + 24], outline=(255, 255, 255, 190), width=3)
    # القرص الموسيقي
    d.ellipse([w - 96, 1470, w - 24, 1542], outline=(255, 255, 255, 190), width=3)
    # الوصف
    d.rectangle([24, 1700, 520, 1740], fill=(255, 255, 255, 150))
    d.rectangle([24, 1760, 400, 1790], fill=(255, 255, 255, 150))
    # الشريط السفلي
    d.rectangle([0, 1850, w, 1920], fill=(0, 0, 0, 170))
    return ov


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", required=True)
    ap.add_argument("--photo", default=None)
    ap.add_argument("--outdir", default="preview")
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)
    size = (1080, 1920)
    frame = Image.open(a.frame).convert("RGBA")
    rng = np.random.default_rng(7)

    bgs = [("light", light_bg(size)), ("dark", dark_bg(size)), ("busy", busy_bg(size, rng)),
           ("checker", checker(size))]
    if a.photo:
        ph = Image.open(a.photo).convert("RGB").resize(size, Image.LANCZOS)
        bgs.insert(0, ("photo", ph))

    for name, bg in bgs:
        out = bg.convert("RGBA")
        out.alpha_composite(frame)
        if name in ("photo", "busy"):
            out.alpha_composite(tiktok_ui(size))
        out.convert("RGB").save(os.path.join(a.outdir, f"preview_{name}.jpg"), quality=92)

    # لوحة تماس (Contact sheet)
    cols, tw, th = 4, 300, 533
    rows = (len(bgs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * 12, rows * th + (rows + 1) * 12), (26, 27, 30))
    for i, (name, bg) in enumerate(bgs):
        t = bg.resize((tw, th), Image.LANCZOS).convert("RGBA")
        f2 = frame.resize((tw, th), Image.LANCZOS)
        t.alpha_composite(f2)
        t = t.convert("RGB")
        r, c = divmod(i, cols)
        sheet.paste(t, (12 + c * (tw + 12), 12 + r * (th + 12)))
    sheet.save(os.path.join(a.outdir, "contact_sheet.jpg"), quality=90)
    print("previews ->", a.outdir)


if __name__ == "__main__":
    main()

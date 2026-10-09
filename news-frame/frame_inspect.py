#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحص نصي للإطار: يطبع خريطة ASCII لكثافة الألفا + يقيس مواضع العناصر بدقة."""
import sys
import numpy as np
from PIL import Image

path = sys.argv[1]
im = Image.open(path).convert("RGBA")
a = np.asarray(im).astype(np.float32)[..., 3] / 255.0
H, W = a.shape
print("size", W, H, "mode", im.mode)

# ---------- خريطة نصية ----------
cols, rows = 60, 68
ch = a[: rows * (H // rows), : cols * (W // cols)].reshape(rows, H // rows, cols, W // cols).mean((1, 3))
ramp = " .:-=+*#%@"
print("\n=== ALPHA MAP (كل خانة ≈ 18x28 بكسل) ===")
for r in range(rows):
    print("".join(ramp[min(9, int(v * 9.999 * 2.2))] for v in ch[r]))

# ---------- قياسات دقيقة ----------
def runs(line, thr=0.15):
    out, start = [], None
    for i, v in enumerate(line):
        if v > thr and start is None:
            start = i
        elif v <= thr and start is not None:
            out.append((start, i - 1)); start = None
    if start is not None:
        out.append((start, len(line) - 1))
    return out

print("\n=== الحافة العلوية y=204 ===")
print(runs(a[204]))
print("y=203,205:", runs(a[203])[:3], runs(a[205])[:3])
print("\n=== الحافة السفلية y=1400 ===")
print(runs(a[1400]))
print("\n=== العمود الأيسر x=64 (مقاطع) ===")
print(runs(a[:, 64]))
print("\n=== العمود الأيمن x=1016 (مقاطع) ===")
print(runs(a[:, 1016]))
print("\n=== لوحة الشعار: صف y=68 ===")
print(runs(a[68]))
print("=== لوحة الشعار: عمود x=1000 ===")
print(runs(a[:, 1000]))
print("\n=== الشفافية ===")
print("interior max alpha:", int(a[300:1350, 210:870].max() * 255))
print("transparent %:", round(100 * float((a == 0).mean()), 3))
print("ink %:", round(100 * float((a > 0.03).mean()), 3))

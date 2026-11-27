"""Sửa các slide còn số liệu cũ của lần kiểm chứng v8 + slide mới bị lỗi dấu."""
from __future__ import annotations

import json
import pathlib
import sys

from pptx import Presentation

ROOT = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer")
PPT = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\TTNT-Nam-Xuân Hải.pptx")
sys.path.insert(0, str(ROOT))

meta = json.loads((ROOT / "models/image/latest.json").read_text(encoding="utf-8"))
http = json.loads((ROOT / "data/reports/v10/http_verification.json").read_text(encoding="utf-8"))
per = {e["label"]: (e["f1"] or 0) for e in meta["metrics"]["test_per_class"]}
counts = meta["dataset"]["counts"]
prs = Presentation(str(PPT))


def set_text(shape, text: str):
    tf = shape.text_frame
    first = tf.paragraphs[0]
    if first.runs:
        first.runs[0].text = text
        for run in first.runs[1:]:
            run.text = ""
    else:
        first.text = text
    for extra in list(tf.paragraphs[1:]):
        extra._p.getparent().remove(extra._p)


def shape_of(slide, shape_id):
    for shape in slide.shapes:
        if shape.shape_id == shape_id:
            return shape
    return None


def vi(x, d=4):
    return f"{float(x):.{d}f}".replace(".", ",")


s21 = prs.slides[20]
SIZE = counts["test"]
EDITS_21 = {
    11: f"{len(meta['labels'])} LỚP", 12: "model đang phục vụ", 13: "MobileNetV3-Small",
    16: "88 ẢNH TEST", 17: "44 lớp × 2 ảnh", 18: "đo qua API thật",
    21: "TOP-1", 22: f"{http['stats']['top1']}/{http['stats']['n']} = "
                      f"{vi(http['stats']['top1'] / http['stats']['n'], 1)} %".replace(".", ","),
    23: "đúng ngay lần đoán đầu",
    26: "TOP-3", 27: f"{http['stats']['top3']}/{http['stats']['n']} = "
                      f"{vi(http['stats']['top3'] / http['stats']['n'], 1)} %".replace(".", ","),
    28: "đúng trong 3 gợi ý",
    31: f"{http['latency_ms_avg']:.0f} ms", 33: "4,4 s",
    35: "Số liệu đo lại trên model v10 đang phục vụ. Lỗi tập trung ở cặp món rất giống nhau "
        "(phở bò · cơm gà · xôi · bánh cuốn · canh chua).",
}
for sid, text in EDITS_21.items():
    s = shape_of(s21, sid)
    if s is not None:
        set_text(s, text)
print("  slide 21: đã sửa", len(EDITS_21), "ô")
# nhãn nhỏ dưới ô độ trễ
s32 = shape_of(s21, 32)
if s32 is not None:
    set_text(s32, "trung bình các lần gọi")

s33 = prs.slides[32]
for sid, text in {17: f"pho_bo F1 = {vi(per['pho_bo'])}",
                  18: "91 ảnh, nhưng món nước rất dễ lẫn với bánh canh và hủ tiếu."}.items():
    s = shape_of(s33, sid)
    if s is not None:
        set_text(s, text)

s37 = prs.slides[36]
s = shape_of(s37, 18)
if s is not None:
    set_text(s, "Quadro P2000 là Pascal sm_61; torch 2.5.1+cu121 còn wheel cho sm_61 nên GPU dùng "
                "được để huấn luyện (34–40 giây/epoch so với 50–75 giây trên CPU). Lần chạy đang dùng: "
                f"{meta['timing']['total_seconds']:,.1f} giây cho {meta['hyperparameters']['epochs_run']} "
                "epoch trên GPU.".replace(",", "."))
s = shape_of(s37, 22)
if s is not None:
    set_text(s, "Vì sao lần chạy báo cáo lại trên CPU?")

s38 = prs.slides[37]
for sid, text in {17: "Lớp 91 ảnh, F1 " + vi(per["pho_bo"]) + ".",
                  18: "Lỗi do món nước rất giống nhau (bánh canh, hủ tiếu) chứ không phải lỗi đường chạy API."}.items():
    s = shape_of(s38, sid)
    if s is not None:
        set_text(s, text)

# slide 41 (mới thêm): sửa bullet bị lỗi dấu
s41 = prs.slides[40]
for shape in s41.shapes:
    if not shape.has_text_frame:
        continue
    for para in shape.text_frame.paragraphs:
        full = "".join(r.text for r in para.runs)
        if "v10 (60 epoch" in full:
            new = (f"v10 (60 epoch, GPU, RandomErasing + label smoothing 0,1): accuracy test "
                   f"{vi(meta['metrics']['test_accuracy'])} · macro F1 "
                   f"{vi(meta['metrics']['test_macro_f1'])} trong "
                   f"{meta['timing']['total_seconds']:,.1f} s.".replace(",", "."))
            if para.runs:
                para.runs[0].text = new
                for run in para.runs[1:]:
                    run.text = ""
            print("  slide 41: đã sửa bullet v10")

prs.save(str(PPT))
print("  đã lưu. slide:", len(prs.slides))

# kiểm tra lại
prs2 = Presentation(str(PPT))
import re
RX = re.compile(r"96,9|98,1|99,1|60,8|7,8 s|23–27|46 ảnh|621,8|25 lớp|0,7000|0,6629|0.7185|0.6917|2\.228\.3")
left = []
for i, slide in enumerate(prs2.slides, 1):
    for shape in slide.shapes:
        if shape.has_text_frame and RX.search(shape.text_frame.text):
            left.append(f"[slide {i}] {shape.text_frame.text[:120]}")
print("  còn lại:", left if left else "không")

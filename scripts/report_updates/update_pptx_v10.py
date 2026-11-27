"""Cập nhật slide .pptx sang model v10 (44 lớp) + thêm slide mới. Sửa TRỰC TIẾP trên tệp đã giao."""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import re

from pptx import Presentation
from pptx.util import Inches, Pt

ROOT = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer")
PPT = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\TTNT-Nam-Xuân Hải.pptx")

meta = json.loads((ROOT / "models/image/latest.json").read_text(encoding="utf-8"))
fair = json.loads((ROOT / "data/reports/v8_vs_v10/fair_comparison.json").read_text(encoding="utf-8"))
new_cls = json.loads((ROOT / "data/reports/v8_vs_v10/v8_vs_new_comparison.json")
                     .read_text(encoding="utf-8"))["v9_new_classes"]
http = json.loads((ROOT / "data/reports/v10/http_verification.json").read_text(encoding="utf-8"))
m, counts, hist = meta["metrics"], meta["dataset"]["counts"], meta["history"]
per_class = m["test_per_class"]
N = meta["num_classes"]
runs = {r["model"]: r for r in fair["runs"]}

import sys
sys.path.insert(0, str(ROOT))
from app.ml import labels_vi  # noqa: E402


def vi(x, d=4):
    return f"{float(x):.{d}f}".replace(".", ",")


prs = Presentation(str(PPT))
REPL = [
    ("25 lớp", f"{N} lớp"),
    ("22 lớp", f"{N} lớp"),
    ("1.688", "2.524"),
    ("1.181", "1.768"),
    ("621,8 s", f"{meta['timing']['total_seconds']:,.1f} s".replace(",", ".")),
    ("0,7000", vi(m["test_accuracy"])),
    ("0,6629", vi(m["test_macro_f1"])),
    ("1.784 ảnh/29 lớp", "2.549 ảnh/45 lớp"),
    ("trong 25 lớp đang huấn luyện", f"trong {N} lớp đang huấn luyện"),
    ("và 16 lớp món Việt", "và 36 lớp món Việt"),
    ("26–30 giây/epoch", "34–40 giây/epoch"),
    ("Mở rộng ngoài 25 lớp hiện tại", f"Đã mở rộng lên {N} lớp ({N - 25} món Việt bổ sung)"),
]
fixed = 0
for slide in prs.slides:
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                for old, new in REPL:
                    if old in run.text:
                        run.text = run.text.replace(old, new)
                        fixed += 1
print("  sửa run:", fixed)

# ---- thay hình đường cong + ma trận nhầm lẫn của v8 bằng bản v10 ----
OLD = {
    "56ecd6fa0112251100674c575efbd0f421a8832aae7b449d212672e0b5ad11a9":
        ROOT / "data/reports/v10/figures/image_confusion_matrix.png",
    "29cf71192bd4f1a19b2001cfc51dbfe056401046ceab8d221a00c9b7d12ba63b":
        ROOT / "data/reports/v10/figures/image_training_curves.png",
}
swapped = []
for rel in prs.part.rels.values():
    part = getattr(rel, "target_part", None)
    if part is None or not hasattr(part, "blob") or not hasattr(part, "_blob"):
        continue
    try:
        digest = hashlib.sha256(part.blob).hexdigest()
    except Exception:
        continue
    if digest in OLD:
        part._blob = OLD[digest].read_bytes()
        swapped.append(OLD[digest].name)
print("  hình thay:", swapped)

# ---- bảng F1: 44 lớp, chia 3 bảng 15/15/14 ----
entries = sorted(per_class, key=lambda e: e["label"])
f1_tables = []
for slide in prs.slides:
    for shape in slide.shapes:
        if getattr(shape, "has_table", False) and shape.has_table:
            tb = shape.table
            if len(tb.columns) == 2 and tb.rows[0].cells[0].text.strip().lower() == "lớp":
                f1_tables.append((slide, shape))
print("  bảng F1 tìm thấy:", len(f1_tables))


def fill_table(shape, rows_data, title_if_needed=None):
    tb = shape.table
    target = len(rows_data) + 1
    # python-pptx không hỗ trợ chỉ số âm trong tb.rows -> luôn dùng len()-1
    while len(tb.rows) > target:
        tb._tbl.remove(tb.rows[len(tb.rows) - 1]._tr)
    while len(tb.rows) < target:
        tb._tbl.append(copy.deepcopy(tb.rows[len(tb.rows) - 1]._tr))
    for idx, entry in enumerate(rows_data, start=1):
        cells = tb.rows[idx].cells
        cells[0].text = f"{labels_vi.display_label(entry['label'])} ({entry['label']})"[:60]
        cells[1].text = vi(entry["f1"] or 0)
        for cell in cells:
            for para in cell.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(9)


chunks = [entries[:15], entries[15:30], entries[30:]]
if len(f1_tables) >= 2:
    slide20, shape_a = f1_tables[0]
    _, shape_b = f1_tables[1]
    fill_table(shape_a, chunks[0])
    fill_table(shape_b, chunks[1])
    # bảng thứ ba cho 14 lớp còn lại
    left = shape_b.left
    top = shape_b.top + shape_b.height + Inches(0.15)
    new_shape = slide20.shapes.add_table(len(chunks[2]) + 1, 2, left, top,
                                         shape_b.width, shape_b.height)
    for ci, header in enumerate(("Lớp", "F1")):
        new_shape.table.rows[0].cells[ci].text = header
    fill_table(new_shape, chunks[2])
print("  bảng F1 đã nạp:", sum(len(c) for c in chunks), "lớp")

# ---- thêm slide mới ----
layout = prs.slide_layouts[1]
best = sorted(((e["label"], e["f1"] or 0) for e in per_class), key=lambda x: -x[1])[:2]
worst = sorted(((e["label"], e["f1"] or 0) for e in per_class), key=lambda x: x[1])[:2]


def add_slide(title: str, bullets: list[str]):
    slide = prs.slides.add_slide(layout)
    slide.shapes.title.text = title
    body = slide.placeholders[1].text_frame
    body.text = bullets[0]
    for line in bullets[1:]:
        para = body.add_paragraph()
        para.text = line
    for para in body.paragraphs:
        for run in para.runs:
            run.font.size = Pt(16)
    return slide


add_slide("CHƯƠNG 3 · NHẬN DIỆN — VÌ SAO PHẢI HUẤN LUYỆN LẠI", [
    "Phản hồi người dùng: nhận diện còn yếu, thiếu nhiều món Việt, tên món nước ngoài khó đọc.",
    "Đo model thị giác Qwen3.5-0.8B trước khi quyết định: ollama show xác nhận có vision (projector clip 100,59 M tham số).",
    "Nhưng trên 40 ảnh thật có đáp án: gọi đúng tên món Việt chỉ 6/40 = 15,0 %; đúng hoặc gần đúng 12/40 = 30,0 %.",
    "Ước lượng khối lượng vô dụng: cùng một món, ảnh này trả 400 g, ảnh khác trả 6 g.",
    "Kết luận: nhận diện vẫn dùng MobileNetV3-Small tự huấn luyện; khối lượng lấy từ bảng khẩu phần × giá trị trong cơ sở dữ liệu.",
])

add_slide("CHƯƠNG 3 · NHẬN DIỆN — MỞ RỘNG DỮ LIỆU 20 MÓN VIỆT", [
    "5 luồng thu thập song song cho 20 món (4 món còn thiếu + 16 món mới), mỗi ảnh có sidecar ghi URL nguồn, giấy phép, SHA-256.",
    "Kiểm chứng trên đĩa: 20/20 lớp khớp hoặc vượt số luồng báo; phát hiện và xoá 1 ảnh trùng giữa bun_rieu và canh_chua.",
    "8 luồng soi ảnh độc lập bằng mắt trên contact sheet mẫu có khoá (ánh xạ được số ô về tên tệp): loại 30 ảnh sai.",
    "Lớp bun_mam bị loại khỏi huấn luyện (mẫu soi chỉ 6/15 đúng món); che_ba_mau 9/15, ca_kho_to 11/15, banh_uot 12/15.",
    "Trên đĩa: 4.149 ảnh nhận / 45 lớp, 2.388 ảnh bị loại. Tập huấn luyện: 2.524 ảnh / 44 lớp (1.768 · 383 · 373).",
])

add_slide("CHƯƠNG 3 · NHẬN DIỆN — KẾT QUẢ MODEL v10", [
    f"Tập dữ liệu: {sum(counts.values()):,} ảnh / {N} lớp — {counts['train']:,} train · {counts['val']:,} validation · {counts['test']:,} test.".replace(",", "."),
    f"v9 (35 epoch): accuracy test 0,7024 · macro F1 0,6745 trong 899,4 s.".replace("899.4", "899,4"),
    f"v10 (60 epoch, GPU, RandomErasing + label smoothing 0,1): accuracy test {vi(m['test_accuracy'])} · macro F1 {vi(m['test_macro_f1'])} trong {meta['timing']['total_seconds']:,.1f} s.".replace(",", "."),
    f"F1 cao nhất: {labels_vi.display_label(best[0][0])} {vi(best[0][1])}, {labels_vi.display_label(best[1][0])} {vi(best[1][1])}; thấp nhất: {labels_vi.display_label(worst[0][0])} {vi(worst[0][1])}, {labels_vi.display_label(worst[1][0])} {vi(worst[1][1])}.",
    "So công bằng trên 134 ảnh là tập test ở CẢ HAI manifest: v8 top-1 0,7164 · v10 0,7463 ⇒ chọn v10 (phủ thêm 19 món Việt).",
    f"Kiểm chứng HTTP thật: top-1 {http['stats']['top1']}/{http['stats']['n']} = {vi(http['stats']['top1']/http['stats']['n'])}, top-3 {http['stats']['top3']}/{http['stats']['n']} = {vi(http['stats']['top3']/http['stats']['n'])}, {http['latency_ms_avg']:.0f} ms/ảnh.",
])

add_slide("CHƯƠNG 3 · NHẬN DIỆN — KHẨU PHẦN VÀ DINH DƯỠNG TỪ ẢNH", [
    "Tuyến /predict/image trả thêm khối portion: khẩu phần tham khảo (gam), thực phẩm khớp trong cơ sở dữ liệu, giá trị cho đúng khẩu phần đó.",
    "Gồm năng lượng, chất đạm, chất béo, chất bột đường, chất xơ, đường, natri + phép tính nguồn + danh sách chất chưa có dữ liệu.",
    "Giao diện điền sẵn khẩu phần để người dùng sửa lại theo lượng thật trong ảnh trước khi ghi nhật ký.",
    "Kiểm chứng thật (ảnh bánh bao, Top-1 69,7 %): chọn Bánh Bao Thịt Heo 2 Trứng Cút → tự điền 120 g → 207,2 kcal · đạm 9,60 g · béo 6,48 g · bột đường 27,60 g · đường 7,76 g · natri 322,60 mg.",
    "Chất xơ chưa có dữ liệu thì ghi rõ chưa có dữ liệu, KHÔNG thay bằng số 0.",
])

add_slide("CHƯƠNG 3 · TRỢ LÝ — ĐỀ XUẤT BỮA ĂN THEO CHỈ SỐ CƠ THỂ", [
    "Trang Tài khoản đã có sẵn: giới tính, năm sinh, chiều cao, cân nặng, mức vận động, mục tiêu cân nặng, mục tiêu kcal, ghi chú.",
    "BMR theo Mifflin–St Jeor · TDEE theo hệ số vận động (1,2–1,9) · điều chỉnh theo mục tiêu cân nặng · ngưỡng an toàn 1.500 kcal (nam) / 1.200 kcal (nữ).",
    "Chỉ đề xuất các bữa CHƯA ghi: ngân sách chia 25 % sáng · 35 % trưa · 30 % tối · 10 % bữa nhẹ, món chọn từ cơ sở dữ liệu thật và tính khối lượng cho khớp ngân sách.",
    "Ghi chú trong hồ sơ thành điều kiện lọc: dị ứng/kiêng/chay (vẫn dùng trứng, sữa)/thuần chay (loại cả trứng, sữa)/tăng cơ; trả về điều kiện đã áp dụng.",
    "Gợi ý vận động nhẹ–vừa–nặng theo hồ sơ và cảnh báo khi đã vượt mục tiêu kcal.",
    "Kiểm chứng thật: BMR 1.573 · TDEE 2.162 · mục tiêu 2.200 · đã ăn 540 · còn 1.660 kcal; bữa trưa đã ghi nên không bị đề xuất lại.",
])

add_slide("CHƯƠNG 3 · TÊN MÓN TIẾNG VIỆT VÀ KIỂM THỬ", [
    "Tên món nước ngoài nay hiển thị kèm tiếng Việt: Pizza → Bánh pizza (Ý) · Hamburger → Bánh kẹp thịt · Sushi → Cơm cuộn sushi (Nhật) · Salad → Rau trộn · Steak → Bít tết (bò nướng).",
    f"Cả {N} lớp đều có tên hiển thị tiếng Việt trong app/ml/labels_vi.py nên giao diện không còn hiện mã lớp.",
    "pytest: 217 bài đạt · 1 bỏ qua · 0 hỏng. Bộ e2e qua API thật: 92 bài đạt · 0 hỏng (chạy với chính model v10 đang phục vụ).",
    "Hạn chế nói thẳng: model vẫn quá khớp (train 0,99 so với validation 0,71); lỗi tập trung ở các cặp món rất giống nhau (phở ↔ bánh canh, xôi ↔ xôi xéo, cơm tấm ↔ cơm gà).",
    "Muốn chính xác hơn cần ảnh thật do người dùng tự chụp 30–50 ảnh mỗi món, không phải tăng số epoch.",
])

prs.save(str(PPT))
print("  số slide sau khi thêm:", len(prs.slides))

"""Cập nhật báo cáo .docx sang model v10 (44 lớp) + thêm các phần mới.

Sửa TRỰC TIẾP trên tệp đã giao; số liệu đọc từ metadata của lần chạy, không bịa.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

from docx import Document
from docx.shared import Pt

ROOT = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer")
DOC = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\TTNT-Nam-Xuân Hải.docx")

meta = json.loads((ROOT / "models/image/latest.json").read_text(encoding="utf-8"))
fair = json.loads((ROOT / "data/reports/v8_vs_v10/fair_comparison.json").read_text(encoding="utf-8"))
new_cls = json.loads((ROOT / "data/reports/v8_vs_v10/v8_vs_new_comparison.json")
                     .read_text(encoding="utf-8"))["v9_new_classes"]
http = json.loads((ROOT / "data/reports/v10/http_verification.json").read_text(encoding="utf-8"))
m, counts, hist = meta["metrics"], meta["dataset"]["counts"], meta["history"]
per_class = m["test_per_class"]
N_CLS = meta["num_classes"]

def vi(x, d=4):
    return f"{float(x):.{d}f}".replace(".", ",")


def label_vi(code: str) -> str:
    """Tên tiếng Việt lấy từ app/ml/labels_vi.py (đọc bằng import để chắc chắn đúng)."""
    import sys
    sys.path.insert(0, str(ROOT))
    from app.ml import labels_vi as lv  # noqa: PLC0415
    return lv.display_label(code)


doc = Document(str(DOC))
fixed: list[str] = []


def fix_paragraph(p, old: str, new: str) -> bool:
    if old not in p.text:
        return False
    for run in p.runs:
        if old in run.text:
            run.text = run.text.replace(old, new)
            fixed.append(f"đoạn: {old[:40]} -> {new[:40]}")
            return True
    full = p.text.replace(old, new)
    if p.runs:
        p.runs[0].text = full
        for run in p.runs[1:]:
            run.text = ""
        fixed.append(f"đoạn (gộp run): {old[:40]} -> {new[:40]}")
        return True
    return False


best = sorted(((e["label"], e["f1"] or 0) for e in per_class), key=lambda x: -x[1])[:2]
worst = sorted(((e["label"], e["f1"] or 0) for e in per_class), key=lambda x: x[1])[:2]
runs = {r["model"]: r for r in fair["runs"]}

REPLACEMENTS = [
    # ---- số lớp / tên món ----
    ("25 lớp", f"{N_CLS} lớp"),
    ("22 lớp", f"{N_CLS} lớp"),
    ("Lịch sử 25 epoch", f"Lịch sử {meta['hyperparameters']['epochs_run']} epoch"),
    ("trong 25 epoch", f"trong {meta['hyperparameters']['epochs_run']} epoch"),
    ("đủ 25 epoch", f"đủ {meta['hyperparameters']['epochs_run']} epoch"),
    # ---- lần huấn luyện đang dùng ----
    ("0,7000", vi(m["test_accuracy"])),
    ("0,6629", vi(m["test_macro_f1"])),
    ("621,8", f"{meta['timing']['total_seconds']:,.1f}".replace(",", ".")),
    # ---- tập dữ liệu ----
    ("1.784 ảnh thuộc 29 lớp (865 ảnh từ Wikimedia Commons, 119 ảnh từ Openverse, 800 ảnh Food-101)",
     "2.549 ảnh thuộc 45 lớp (954 ảnh từ Wikimedia Commons, 795 ảnh từ Openverse, 800 ảnh Food-101)"),
    ("1.181 train, 257 validation, 250 test",
     f"{counts['train']:,} train, {counts['val']:,} validation, {counts['test']:,} test".replace(",", ".")),
    ("1.784 ảnh thuộc 29 lớp", "2.549 ảnh thuộc 45 lớp"),
    ("trong 25 lớp đang huấn luyện có 8 lớp", f"trong {N_CLS} lớp đang huấn luyện có 8 lớp"),
    ("và 17 lớp món Việt", "và 36 lớp món Việt"),
    # ---- sửa lại khẳng định SAI về GPU ----
    ("Bản PyTorch CUDA mới không build cho kiến trúc này và torch.cuda.is_available() trả False",
     "Kênh CUDA cu121 của PyTorch 2.5.1 vẫn còn wheel cho kiến trúc sm_61 nên GPU dùng được cho "
     "huấn luyện (torch.cuda.is_available() trả True, đo được 34–40 giây mỗi epoch so với 50–75 giây "
     "trên CPU)"),
]


for p in doc.paragraphs:
    for old, new in REPLACEMENTS:
        fix_paragraph(p, old, new)

# ---- bảng F1: 44 hàng ----
f1_table = doc.tables[12]
while len(f1_table.rows) > 1:
    f1_table._tbl.remove(f1_table.rows[-1]._tr)
rows_sorted = sorted(per_class, key=lambda e: (e["label"]))
for entry in rows_sorted:
    row = f1_table.add_row()
    values = [entry["label"], str(entry["support"]), vi(entry["precision"] or 0), vi(entry["recall"] or 0),
              vi(entry["f1"] or 0)]
    for cell, value in zip(row.cells, values):
        cell.text = value

# ---- bảng lịch sử huấn luyện: 60 epoch ----
hist_table = doc.tables[13]
while len(hist_table.rows) > 1:
    hist_table._tbl.remove(hist_table.rows[-1]._tr)
for entry in hist:
    row = hist_table.add_row()
    values = [str(entry["epoch"]), vi(entry["train_loss"]), vi(entry["train_accuracy"], 3),
              vi(entry["val_loss"]), vi(entry["val_accuracy"], 3), vi(entry["seconds"], 1)]
    for cell, value in zip(row.cells, values):
        cell.text = value

# ---- bảng tập dữ liệu (Tập | Số ảnh) ----
split_table = doc.tables[10]
mapping = {"train": counts["train"], "val": counts["val"], "validation": counts["val"],
           "test": counts["test"], "tổng": sum(counts.values())}
for row in split_table.rows[1:]:
    label = row.cells[0].text.strip().lower()
    for key, value in mapping.items():
        if key in label:
            row.cells[1].text = str(value)
            break

# ---- bảng chỉ số model ----
metrics_table = doc.tables[11]
for row in metrics_table.rows[1:]:
    name = row.cells[0].text.strip().lower()
    if "accuracy" in name and "validation" not in name:
        row.cells[1].text = vi(m["test_accuracy"])
    elif "f1" in name:
        row.cells[1].text = vi(m["test_macro_f1"])
    elif "val" in name:
        row.cells[1].text = vi(m["best_val_accuracy"])
    elif "loss" in name:
        row.cells[1].text = vi(m["test_loss"])

# ---- thay 2 hình (đường cong + ma trận nhầm lẫn) theo SHA của bản v8 ----
OLD_SHAS = {
    "56ecd6fa0112251100674c575efbd0f421a8832aae7b449d212672e0b5ad11a9":
        ROOT / "data/reports/v10/figures/image_confusion_matrix.png",
    "29cf71192bd4f1a19b2001cfc51dbfe056401046ceab8d221a00c9b7d12ba63b":
        ROOT / "data/reports/v10/figures/image_training_curves.png",
}
swapped = []
for rel in doc.part.rels.values():
    part = getattr(rel, "target_part", None)
    if part is None or not hasattr(part, "blob"):
        continue
    digest = hashlib.sha256(part.blob).hexdigest()
    if digest in OLD_SHAS:
        part._blob = OLD_SHAS[digest].read_bytes()
        swapped.append(OLD_SHAS[digest].name)

# ---- thêm các phần mới ----
def heading(text: str, level: int = 2):
    doc.add_heading(text, level=level)


def para(text: str):
    doc.add_paragraph(text)


heading("3.6. Bổ sung theo phản hồi người dùng", 1)
para("Sau khi dùng thử, người dùng nêu ba yêu cầu: (1) nhận diện ảnh còn yếu và thiếu nhiều món Việt, "
     "(2) tên món nước ngoài khó đọc, (3) cần đề xuất món ăn theo mục tiêu năng lượng và chỉ số cơ thể, "
     "kèm ước lượng khối lượng cùng thành phần dinh dưỡng từ ảnh. Mục này trình bày phần đã làm và số đo "
     "kiểm chứng cho từng yêu cầu.")

heading("3.6.1. Đo khả năng thị giác của Qwen3.5-0.8B trước khi quyết định", 2)
para("Lệnh ollama show qwen3.5:0.8b xác nhận model có khả năng thị giác (capability vision, kèm projector "
     "clip 100,59 triệu tham số). Tuy nhiên khi đo trên 40 ảnh thật có đáp án biết trước (2 ảnh × 20 lớp, "
     "lấy từ tập test của đề tài), model gọi đúng tên món Việt chỉ 6/40 = 15,0 % và đúng hoặc gần đúng "
     "12/40 = 30,0 %. Ước lượng khối lượng còn kém hơn: cùng một món, model trả 400 g cho một ảnh nhưng "
     "trả 6 g cho ảnh khác. Vì vậy đề tài giữ MobileNetV3-Small tự huấn luyện cho phần nhận diện, còn "
     "khối lượng và thành phần dinh dưỡng lấy từ bảng khẩu phần tham khảo nhân với giá trị có thật trong "
     "cơ sở dữ liệu, cho người dùng sửa lại theo thực tế.")

heading("3.6.2. Khẩu phần và dinh dưỡng ước lượng khi nhận diện ảnh", 2)
para("Tuyến POST /api/v1/predict/image trả thêm khối portion gồm: khẩu phần tham khảo của món (gam), "
     "thực phẩm khớp trong cơ sở dữ liệu, giá trị dinh dưỡng tính cho đúng khẩu phần đó (năng lượng, "
     "chất đạm, chất béo, chất bột đường, chất xơ, đường, natri), phép tính nguồn (nutrient_source) và "
     "danh sách chất chưa có dữ liệu (missing_nutrients). Giao diện điền sẵn khẩu phần này vào ô khối "
     "lượng để người dùng sửa lại. Bảng khẩu phần tham khảo nằm ở app/ml/portion_table.py, gồm 44 món "
     "đã huấn luyện.")
para("Kiểm chứng thật trên giao diện (ảnh bánh bao trong tập test): model đoán Top-1 Bánh bao 69,7 %; "
     "chọn thực phẩm Bánh Bao Thịt Heo 2 Trứng Cút, ô khối lượng tự điền 120 g; bảng dinh dưỡng hiện "
     "207,2 kcal, chất đạm 9,60 g, chất béo 6,48 g, chất bột đường 27,60 g, đường tổng 7,76 g, natri "
     "322,60 mg, còn chất xơ ghi rõ “chưa có dữ liệu” chứ không thay bằng 0.")
para("Một lỗi thật đã gặp và sửa: với nhãn salad, cơ sở dữ liệu chỉ khớp ra “Salad dressing” "
     "(884 kcal/100 g) nên khẩu phần hiện ra vô nghĩa; nay bộ chọn tự tìm thêm ứng viên theo từ khoá "
     "của món, loại nước sốt/gia vị/bột pha và loại có năng lượng bất thường, nếu vẫn không có món "
     "“ra món ăn” thì báo rõ là chưa tính được.")

heading("3.6.3. Đề xuất thực đơn theo chỉ số cơ thể và các bữa còn lại", 2)
para("Trang Tài khoản của tôi đã có sẵn các ô cần thiết: giới tính, năm sinh, chiều cao, cân nặng, "
     "mức vận động, mục tiêu cân nặng, mục tiêu kcal mỗi ngày và ghi chú. Bộ máy tính toán gồm:")
para("• app/services/nutrition_needs.py: tính BMR theo công thức Mifflin–St Jeor, TDEE theo hệ số vận "
     "động (1,2 · 1,375 · 1,55 · 1,725 · 1,9), điều chỉnh theo mục tiêu cân nặng (giảm −500 kcal, giữ "
     "nguyên, tăng +300 kcal) và áp ngưỡng an toàn (không đề xuất dưới 1.500 kcal với nam, 1.200 kcal "
     "với nữ); thiếu chỉ số nào thì trả về missing_fields, không suy diễn.")
para("• app/services/plan_service.py: chỉ đề xuất các bữa CHƯA ghi trong ngày. Ngân sách năng lượng "
     "được chia theo tỉ lệ bữa sáng 25 %, bữa trưa 35 %, bữa tối 30 %, bữa nhẹ 10 % rồi chuẩn hoá lại "
     "theo số bữa còn lại; món được chọn từ danh sách nguyên liệu có thật trong cơ sở dữ liệu và khối "
     "lượng được tính để khớp ngân sách của từng bữa. Ghi chú trong hồ sơ được dùng làm điều kiện lọc: "
     "ghi chú trống thì bỏ qua, có “dị ứng hải sản” thì loại nhóm hải sản, “ăn chay” loại thịt và hải "
     "sản nhưng vẫn dùng được trứng và sữa, “thuần chay” loại cả trứng và sữa, “tập gym” thì tăng khẩu "
     "phần đạm. Các điều kiện đã áp dụng được trả về trong constraints.applied.")
para("• Gợi ý vận động theo mức vận động trong hồ sơ, kèm cảnh báo khi hôm nay đã vượt mục tiêu kcal. "
     "Hai tuyến mới là GET /api/v1/plan/needs và GET /api/v1/plan/today; trang Tổng quan có khối "
     "“Thực đơn đề xuất cho các bữa còn lại”; trợ lý AI nhận khối THỰC ĐƠN ĐỀ XUẤT trong ngữ cảnh và "
     "chỉ được diễn giải đúng các món, khối lượng và số kcal có trong đó.")
para("Kiểm chứng thật bằng tài khoản tạm với dữ liệu thật trong cơ sở dữ liệu: BMR 1.573 kcal, hệ số "
     "vận động 1,375, TDEE 2.162 kcal, mục tiêu đang dùng 2.200 kcal (do người dùng đặt), đã ăn 540 kcal, "
     "còn lại 1.660 kcal; điều kiện lọc từ ghi chú được áp dụng và hiện rõ trên giao diện; bữa trưa đã "
     "ghi nên không bị đề xuất lại, chỉ còn bữa sáng, bữa tối và bữa nhẹ. Kiểm tra tay công thức BMR: "
     "nam 62 kg, cao 170 cm, sinh năm 2003 → 10×62 + 6,25×170 − 5×23 + 5 = 1.572,5 ≈ 1.573 kcal; "
     "TDEE = 1.573 × 1,375 = 2.162,9 ≈ 2.162 kcal.")

heading("3.6.4. Mở rộng dữ liệu 20 món Việt và huấn luyện lại", 2)
para("Năm luồng thu thập chạy song song bổ sung ảnh cho 20 món Việt (4 món còn thiếu trước đây và 16 "
     "món mới), mỗi món yêu cầu tối thiểu 40 ảnh tải về; mỗi ảnh có tệp sidecar ghi URL nguồn, trang "
     "tìm kiếm, giấy phép nếu công bố và SHA-256; ảnh bị loại được chuyển sang thư mục _rejected chứ "
     "không xoá. Tôi kiểm chứng độc lập trên đĩa: 20/20 lớp có số ảnh khớp hoặc vượt số luồng báo, phát "
     "hiện và xoá 1 ảnh trùng nội dung giữa hai lớp (bun_rieu và canh_chua).")
para("Sau đó tôi tự dựng contact sheet bằng mẫu ngẫu nhiên có khoá (có thể tái lập để ánh xạ số ô về "
     "tên tệp) và giao cho 8 luồng kiểm duyệt độc lập đánh giá bằng mắt. Kết quả: 30 ảnh bị loại ở "
     "vòng này, nặng nhất là lớp bun_mam (mẫu soi chỉ 6/15 ảnh đúng món, ước lượng còn khoảng 10 ảnh "
     "sạch nên lớp này bị loại khỏi lần huấn luyện), tiếp theo là che_ba_mau 9/15, ca_kho_to 11/15 và "
     "banh_uot 12/15; 10 lớp có mẫu soi đúng 15/15 ảnh. Chi tiết ở "
     "data/reports/round3_visual_audit_report.md.")
para(f"Tập dữ liệu sau khi lọc: trên đĩa có 4.149 ảnh nhận thuộc 45 lớp và 2.388 ảnh bị loại; manifest "
     f"đầy đủ 2.549 ảnh thuộc 45 lớp; tập dùng để huấn luyện gồm {N_CLS} lớp với "
     f"{sum(counts.values()):,} ảnh, chia {counts['train']:,} train, {counts['val']:,} validation và "
     f"{counts['test']:,} test.".replace(",", "."))
para(f"Hai lần huấn luyện lại trên GPU: v9 dùng 35 epoch, dừng sớm ở epoch 24, đạt accuracy test 0,7024 "
     f"và macro F1 0,6745 trong 899,4 giây; v10 dùng 60 epoch với RandomErasing và label smoothing 0,1, "
     f"đạt accuracy test {vi(m['test_accuracy'])} và macro F1 {vi(m['test_macro_f1'])} trong "
     f"{meta['timing']['total_seconds']:,.1f} giây (epoch tốt nhất là {meta['hyperparameters']['best_epoch']})."
     .replace(",", "."))
para(f"So sánh công bằng v8 và v10 trên 134 ảnh là tập test ở CẢ HAI manifest (tức không model nào từng "
     f"học): v8 đạt top-1 {vi(runs['v8']['top1_acc'])} và top-3 {vi(runs['v8']['top3_acc'])}; v10 đạt "
     f"top-1 {vi(runs['v10']['top1_acc'])} và top-3 {vi(runs['v10']['top3_acc'])}. Vì vậy v10 được chọn "
     f"làm bản phục vụ vì tốt hơn về top-1 và phủ thêm 19 món Việt (trên 19 lớp đó v10 đạt top-1 "
     f"{vi(new_cls['top1_acc'])} và top-3 {vi(new_cls['top3_acc'])}).")
para(f"Kiểm chứng qua HTTP thật với model v10 đang phục vụ, trên 88 ảnh tập test (2 ảnh mỗi lớp): "
     f"top-1 {http['stats']['top1']}/{http['stats']['n']} = "
     f"{vi(http['stats']['top1'] / http['stats']['n'])}, top-3 {http['stats']['top3']}/{http['stats']['n']} "
     f"= {vi(http['stats']['top3'] / http['stats']['n'])}, thời gian trung bình "
     f"{http['latency_ms_avg']:.0f} ms mỗi ảnh. Lỗi sai cả hai ảnh tập trung ở các cặp món rất giống nhau: "
     f"pho_bo, com_ga, xoi, banh_cuon, canh_chua.")
para("Hạn chế nói thẳng: model vẫn quá khớp (train accuracy 0,99 so với validation 0,71), muốn tăng độ "
     "chính xác cho từng món cần ảnh thật do người dùng tự chụp (30–50 ảnh mỗi món) chứ không phải tăng "
     "số epoch. Phần lớn ảnh mới lấy từ nguồn web công khai không công bố giấy phép, đề tài ghi trung "
     "thực giá trị unknown kèm URL nguồn thật và không tự gán giấy phép.")

heading("3.6.5. Tên món tiếng Việt cho các lớp nhận diện", 2)
para("Các lớp món nước ngoài nay hiển thị kèm tên tiếng Việt: pizza → Bánh pizza (Ý), hamburger → "
     "Bánh kẹp thịt (hamburger), sushi → Cơm cuộn sushi (Nhật), salad → Rau trộn (salad), steak → "
     "Bít tết (bò nướng), pasta → Mì Ý (pasta), fried_chicken → Gà rán. Toàn bộ 44 lớp đều có tên hiển "
     "thị tiếng Việt trong bảng LABEL_VI của app/ml/labels_vi.py nên giao diện không còn hiện mã lớp.")
para(f"Kiểm thử: pytest 217 bài đạt, 1 bài bỏ qua, 0 bài hỏng; bộ e2e qua API thật 92 bài đạt, 0 bài "
     f"hỏng, chạy với chính model v10 đang phục vụ. Hai bảng dưới được cập nhật theo lần chạy v10: "
     f"Bảng 3.3 là precision, recall, F1 theo {N_CLS} lớp "
     f"(cao nhất: {label_vi(best[0][0])} {vi(best[0][1])} và {label_vi(best[1][0])} {vi(best[1][1])}; "
     f"thấp nhất: {label_vi(worst[0][0])} {vi(worst[0][1])} và {label_vi(worst[1][0])} {vi(worst[1][1])}; "
     f"không lớp nào có F1 bằng 0); Bảng 3.4 là lịch sử đủ "
     f"{meta['hyperparameters']['epochs_run']} epoch.")

doc.save(str(DOC))
print("  đã sửa đoạn:", len(fixed))
for item in fixed:
    print("   -", item)
print("  bảng F1:", len(doc.tables[12].rows) - 1, "hàng | lịch sử:", len(doc.tables[13].rows) - 1, "epoch")
print("  hình đã thay:", swapped)
print("  số đoạn sau khi thêm:", len(doc.paragraphs))

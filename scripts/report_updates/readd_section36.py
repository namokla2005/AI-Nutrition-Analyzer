"""Chèn lại mục 3.6 (đo thị giác 0,8B, khẩu phần từ ảnh, đề xuất thực đơn, mở rộng 20 món Việt) — bản gọn."""
from __future__ import annotations

import json
import pathlib

from docx import Document
from docx.shared import Pt

ROOT = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer")
DOC = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\TTNT-Nam-Xuân Hải.docx")
meta = json.loads((ROOT / "models/image/latest.json").read_text(encoding="utf-8"))
http = json.loads((ROOT / "data/reports/v10/http_verification.json").read_text(encoding="utf-8"))
m = meta["metrics"]
counts = meta["dataset"]["counts"]

doc = Document(str(DOC))
# tìm đoạn "KẾT LUẬN" để chèn ngay trước
idx = next(i for i, p in enumerate(doc.paragraphs) if p.text.strip() == "KẾT LUẬN")
anchor = doc.paragraphs[idx]._element

new_blocks = [
    ("h", "3.6. Bổ sung theo phản hồi người dùng"),
    ("p", "Sau khi dùng thử, người dùng nêu ba yêu cầu: nhận diện ảnh còn yếu và thiếu nhiều món Việt, tên "
          "món nước ngoài khó đọc, và cần đề xuất món ăn theo mục tiêu năng lượng cùng chỉ số cơ thể kèm ước "
          "lượng khối lượng, thành phần dinh dưỡng từ ảnh."),
    ("b", "Đo khả năng thị giác của trợ lý trước khi quyết định: lệnh ollama show qwen3.5:0.8b xác nhận model "
          "có khả năng thị giác (projector clip 100,59 triệu tham số), nhưng trên 40 ảnh thật có đáp án model "
          "gọi đúng tên món Việt chỉ 6/40 = 15,0 % và ước lượng khối lượng vô dụng (cùng một món: 400 g ở ảnh "
          "này, “6 g” ở ảnh khác). Vì vậy nhận diện vẫn dùng CNN tự huấn luyện, còn khối lượng lấy từ bảng "
          "khẩu phần tham khảo nhân với giá trị có thật trong cơ sở dữ liệu và cho người dùng sửa lại."),
    ("b", "Khẩu phần và dinh dưỡng khi nhận diện ảnh: tuyến POST /api/v1/predict/image trả thêm khối portion "
          "gồm khẩu phần tham khảo (gam), thực phẩm khớp trong cơ sở dữ liệu, giá trị dinh dưỡng tính cho đúng "
          "khẩu phần đó (năng lượng, chất đạm, chất béo, chất bột đường, chất xơ, đường, natri), phép tính nguồn "
          "và danh sách chất chưa có dữ liệu; giao diện điền sẵn khẩu phần để người dùng sửa. Kiểm chứng thật "
          "trên giao diện (ảnh bánh bao, Top-1 69,7 %): chọn thực phẩm Bánh Bao Thịt Heo 2 Trứng Cút, khối "
          "lượng tự điền 120 g, kết quả 207,2 kcal · chất đạm 9,60 g · chất béo 6,48 g · chất bột đường 27,60 g "
          "· đường tổng 7,76 g · natri 322,60 mg, chất xơ ghi rõ “chưa có dữ liệu”. Một lỗi thật đã sửa: nhãn "
          "salad từng khớp ra “Salad dressing” (884 kcal/100 g) nên khẩu phần vô nghĩa."),
    ("b", "Đề xuất thực đơn theo chỉ số cơ thể: app/services/nutrition_needs.py tính BMR theo Mifflin–St Jeor, "
          "TDEE theo hệ số vận động (1,2–1,9), điều chỉnh theo mục tiêu cân nặng và áp ngưỡng an toàn "
          "(1.500 kcal với nam, 1.200 kcal với nữ; thiếu chỉ số thì trả missing_fields, không suy diễn). "
          "app/services/plan_service.py chỉ đề xuất các bữa CHƯA ghi trong ngày, chia ngân sách năng lượng "
          "25 % sáng · 35 % trưa · 30 % tối · 10 % bữa nhẹ, chọn nguyên liệu có thật trong cơ sở dữ liệu và "
          "tính khối lượng cho khớp ngân sách từng bữa; ghi chú trong hồ sơ được dùng làm điều kiện lọc "
          "(dị ứng, kiêng, ăn chay vẫn dùng trứng và sữa, thuần chay loại cả trứng và sữa, tăng cơ) và trả về "
          "constraints.applied; kèm gợi ý vận động theo hồ sơ. Kiểm chứng thật: BMR 1.573 kcal · TDEE 2.162 "
          "kcal · mục tiêu 2.200 kcal · đã ăn 540 kcal · còn lại 1.660 kcal; bữa trưa đã ghi nên không bị đề "
          "xuất lại, chỉ còn bữa sáng, bữa tối và bữa nhẹ."),
    ("b", f"Mở rộng dữ liệu 20 món Việt và huấn luyện lại: năm luồng thu thập song song bổ sung ảnh cho 20 món "
          f"(4 món còn thiếu và 16 món mới), mỗi ảnh có sidecar ghi URL nguồn, giấy phép và mã băm; kiểm chứng "
          f"trên đĩa cho thấy 20/20 lớp khớp hoặc vượt số luồng báo và phát hiện 1 ảnh trùng giữa hai lớp. Tám "
          f"luồng kiểm duyệt độc lập soi ảnh bằng mắt (contact sheet mẫu có khoá để ánh xạ số ô về tên tệp) "
          f"loại 30 ảnh sai; lớp bun_mam bị loại khỏi huấn luyện vì mẫu soi chỉ 6/15 ảnh đúng món. Tập huấn "
          f"luyện gồm {meta['num_classes']} lớp với {sum(counts.values()):,} ảnh ("
          f"{counts['train']:,} train · {counts['val']:,} validation · {counts['test']:,} test). Vòng huấn luyện "
          f"v10 dùng 60 epoch trên GPU với RandomErasing và label smoothing 0,1, đạt accuracy test "
          f"{m['test_accuracy']:.4f} và macro F1 {m['test_macro_f1']:.4f} trong "
          f"{meta['timing']['total_seconds']:,.1f} giây; so sánh công bằng với bản 25 lớp trên 134 ảnh là tập "
          f"test ở cả hai manifest cho kết quả 0,7463 so với 0,7164 nên bản 44 lớp được chọn, phủ thêm 19 món "
          f"Việt. Kiểm chứng qua HTTP thật: top-1 {http['stats']['top1']}/{http['stats']['n']} = 75,0 %, top-3 "
          f"{http['stats']['top3']}/{http['stats']['n']} = 80,7 %, trung bình 92 ms mỗi ảnh.".replace(",", ".")),
    ("b", "Tên món tiếng Việt và kiểm thử: các lớp món nước ngoài nay hiển thị kèm tên tiếng Việt (pizza → "
          "Bánh pizza (Ý), hamburger → Bánh kẹp thịt, sushi → Cơm cuộn sushi (Nhật), salad → Rau trộn, "
          "steak → Bít tết (bò nướng)); cả 44 lớp đều có tên hiển thị tiếng Việt trong app/ml/labels_vi.py. "
          "Kiểm thử: pytest 217 bài đạt · 1 bỏ qua · 0 hỏng; bộ kiểm thử đầu-cuối qua API thật 92 bài đạt · "
          "0 hỏng với chính model đang phục vụ."),
]

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

prev = anchor
for kind, text in new_blocks:
    p = OxmlElement("w:p")
    prev.addprevious(p)
    prev = p
# gán chữ theo thứ tự vừa chèn
start = idx
for offset, (kind, text) in enumerate(new_blocks):
    para = doc.paragraphs[start + offset]
    para.text = text
    if kind == "h":
        para.style = doc.styles["Heading 2"]
    else:
        para.paragraph_format.line_spacing = 1.15
        para.paragraph_format.space_after = Pt(4)
        if kind == "b":
            para.paragraph_format.left_indent = Pt(14)
doc.save(str(DOC))
print("  đã chèn mục 3.6 với", len(new_blocks), "đoạn")
check = Document(str(DOC))
i = next(i for i, p in enumerate(check.paragraphs) if p.text.strip().startswith("3.6."))
for p in check.paragraphs[i:i + len(new_blocks)]:
    print("   -", p.text[:100])

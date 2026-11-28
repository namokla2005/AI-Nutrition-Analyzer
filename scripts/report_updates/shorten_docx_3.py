"""Cắt gọn sâu: bỏ mục 2.6 (nhật ký triển khai), nén bảng, thu nhỏ hình, giãn dòng 1,0."""
from __future__ import annotations

import pathlib
import re

from docx import Document
from docx.shared import Pt

DOC = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\TTNT-Nam-Xuân Hải.docx")
doc = Document(str(DOC))


def find_index(prefix: str, start: int = 0, max_len: int = 70):
    for i in range(start, len(doc.paragraphs)):
        t = doc.paragraphs[i].text.strip()
        if t.startswith(prefix) and len(t) < max_len:
            return i
    return None


body = find_index("CHƯƠNG 1.")
i26 = find_index("2.6.", body)
i27 = find_index("2.7.", body)
print("  vị trí 2.6:", i26, "| 2.7:", i27)

if i26 is not None and i27 is not None and i27 > i26:
    replaced = (
        "2.6. Quy trình triển khai thực tế (tóm tắt)",
        "Quá trình làm đề tài trải qua 12 bước, ghi lại đầy đủ trong BAO_CAO_KIEM_THU.md kèm bằng chứng "
        "(số dòng, mã băm, ảnh chụp): dựng môi trường Python 3.12.8 và các thư viện (FastAPI, SQLAlchemy, "
        "Alembic, PyTorch, scikit-learn, Jinja2, Chart.js); tạo migration 827db6071a8d và nạp 102.847 thực "
        "phẩm từ USDA và Open Food Facts; dựng tập ảnh (2.549 ảnh/45 lớp, chia train–validation–test cố "
        "định) và kiểm toán bằng mắt từng lớp; huấn luyện nhận diện ảnh (MobileNetV3-Small, transfer "
        "learning) và bốn mô hình hồi quy năng lượng; viết backend theo kiến trúc modular monolith và 9 "
        "trang giao diện tiếng Việt; nối trợ lý Qwen3.5-0.8B qua Ollama ở địa chỉ loopback; thêm lớp kiểm "
        "chứng số liệu cho trợ lý; bổ sung bộ máy đề xuất thực đơn theo chỉ số cơ thể và ước lượng khẩu "
        "phần từ ảnh; cuối cùng là 217 bài kiểm thử tự động, 92 bài kiểm thử đầu-cuối và đóng gói tài liệu.",
        "Các lỗi thật đã gặp và cách sửa được liệt kê trong bảng dưới đây và chi tiết ở BAO_CAO_KIEM_THU.md.",
    )
    # giữ 1 đoạn tiêu đề + 1 đoạn tóm tắt, xoá phần nhật ký
    doc.paragraphs[i26].text = replaced[0]
    doc.paragraphs[i26 + 1].text = " ".join(replaced[1:])
    for i in range(i27 - 1, i26 + 1, -1):
        doc.paragraphs[i]._element.getparent().remove(doc.paragraphs[i]._element)
    print("  đã thay 2.6 bằng tóm tắt")

# nén bảng
diag = []
cut = 0
for tb in doc.tables:
    head = " ".join(c.text.strip().replace("\n", " ") for c in tb.rows[0].cells)
    nrow, ncol = len(tb.rows), len(tb.columns)
    diag.append(f"{nrow}x{ncol}: {head[:60]}")
    target = None
    if "Ký hiệu" in head and nrow > 16:
        target = 16
    elif "Epoch" in head and ncol >= 6 and nrow > 14:
        target = 14
    elif "Phương" in head and ncol >= 5 and nrow > 11:
        target = 11
    elif head.startswith("Số liệu") and nrow > 18:
        target = 18
    if target:
        for row in list(tb.rows[target:len(tb.rows)]):
            tb._tbl.remove(row._tr)
            cut += 1
print("  hàng bảng đã bỏ:", cut)

# thu nhỏ hình + giãn dòng
for shape in doc.inline_shapes:
    shape.width = int(shape.width * 0.72)
    shape.height = int(shape.height * 0.72)
for p in doc.paragraphs:
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(3)
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.space_after = Pt(0)

doc.save(str(DOC))
print("  đoạn:", len(Document(str(DOC)).paragraphs), "| bảng:", len(Document(str(DOC)).tables),
      "| hình:", len(Document(str(DOC)).inline_shapes))
print("\n  Bảng hiện có:")
for d in diag:
    print("   ", d)

"""Đưa bản dựng lại từ PDF vào vị trí + cắt gọn (bảng, hình, phụ lục, giãn dòng)."""
from __future__ import annotations

import pathlib
import re
import shutil

from docx import Document
from docx.shared import Pt

SRC = pathlib.Path(r"C:\Users\Nam\AppData\Local\hermes\cache\scratch\verify3\rebuilt_from_pdf.docx")
DOC = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\TTNT-Nam-Xuân Hải.docx")
shutil.copy(SRC, DOC)
doc = Document(str(DOC))

# 1) bỏ dòng đầu trang/chân trang lặp và số trang rời
HEADER = re.compile(r"^Báo cáo bài tập lớn\s*[–-]\s*Trí tuệ nhân tạo\s*$")
removed = 0
for p in list(doc.paragraphs):
    t = p.text.strip()
    if HEADER.match(t) or re.fullmatch(r"\d{1,3}", t):
        p._element.getparent().remove(p._element)
        removed += 1
print("  bỏ dòng đầu/chân trang:", removed)

# 2) tìm vị trí các mục lớn trong thân bài (bỏ qua phần mục lục)
paras = doc.paragraphs
body_start = next(i for i, p in enumerate(paras) if p.text.strip().startswith("DANH MỤC THUẬT NGỮ"))


def find_index(prefix: str, start: int) -> int | None:
    for i in range(start, len(doc.paragraphs)):
        t = doc.paragraphs[i].text.strip()
        if t.startswith(prefix) and len(t) < 70:
            return i
    return None


idx_b = find_index("PHỤ LỤC B.", body_start)
idx_d = find_index("PHỤ LỤC D.", body_start)
idx_e = find_index("PHỤ LỤC E.", body_start)
print("  vị trí: B", idx_b, "| D", idx_d, "| E", idx_e)

# 3) xoá các đoạn của phụ lục B, C, E (giữ bảng nằm trong khoảng đó cũng bị bỏ theo)
def drop_range(start: int | None, end: int | None):
    if start is None:
        return 0
    stop = end if end is not None else len(doc.paragraphs)
    dropped = 0
    for i in range(stop - 1, start - 1, -1):
        if i < len(doc.paragraphs):
            doc.paragraphs[i]._element.getparent().remove(doc.paragraphs[i]._element)
            dropped += 1
    return dropped


dropped_e = drop_range(idx_e, None)
dropped_bc = drop_range(idx_b, idx_d)
print("  bỏ phụ lục E:", dropped_e, "| B+C:", dropped_bc)

# 4) cắt bảng lớn
def trim(table, keep_head: int, keep_last: int = 0):
    rows = table.rows
    target = 1 + keep_head + keep_last
    if len(rows) <= target:
        return 0
    for row in list(rows[1 + keep_head:len(rows) - keep_last]):
        table._tbl.remove(row._tr)
    return len(rows) - target


cut = 0
for tb in doc.tables:
    head = " | ".join(c.text.strip()[:14] for c in tb.rows[0].cells)
    ncol = len(tb.columns)
    nrow = len(tb.rows)
    if head.startswith("Ký hiệu") and nrow > 18:          # danh mục thuật ngữ
        cut += trim(tb, 15)
    elif "Epoch" in head and ncol >= 6:                    # lịch sử huấn luyện
        cut += trim(tb, 12)
    elif "Phương" in head and ncol >= 5:                   # bảng phân quyền API
        cut += trim(tb, 10)
    elif head.startswith("Số liệu") and nrow > 20:         # bảng truy nguồn số liệu
        cut += trim(tb, 16)
print("  hàng bảng đã bỏ:", cut)

# 5) thu nhỏ hình 0,75 và giãn dòng gọn
for shape in doc.inline_shapes:
    shape.width = int(shape.width * 0.75)
    shape.height = int(shape.height * 0.75)
for p in doc.paragraphs:
    pf = p.paragraph_format
    pf.line_spacing = 1.15
    pf.space_after = Pt(4)
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.space_after = Pt(0)

doc.save(str(DOC))
check = Document(str(DOC))
print("  đoạn:", len(check.paragraphs), "| bảng:", len(check.tables), "| hình:", len(check.inline_shapes))

"""Gán style tiêu đề cho bản dựng lại + chèn mục lục thật (Word COM) + kiểm kê hình."""
from __future__ import annotations

import pathlib
import re

import win32com.client as win32
from docx import Document

DOC = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\TTNT-Nam-Xuân Hải.docx")
doc = Document(str(DOC))

H1 = re.compile(r"^(CHƯƠNG\s+\d+\.|KẾT LUẬN$|TÀI LIỆU THAM KHẢO$|PHỤ LỤC\s+[A-Z]\.|LỜI NÓI ĐẦU$|MỤC LỤC$|DANH MỤC THUẬT NGỮ)")
H2 = re.compile(r"^\d+\.\d+\.\s+\S")
H3 = re.compile(r"^\d+\.\d+\.\d+\.\s+\S")

counts = {"1": 0, "2": 0, "3": 0}
toc_start = None
for i, p in enumerate(doc.paragraphs):
    t = p.text.strip()
    if not t or len(t) > 90:
        continue
    if t.startswith("MỤC LỤC"):
        toc_start = i
    if H1.match(t):
        p.style = doc.styles["Heading 1"]
        counts["1"] += 1
    elif H3.match(t):
        p.style = doc.styles["Heading 3"]
        counts["3"] += 1
    elif H2.match(t):
        p.style = doc.styles["Heading 2"]
        counts["2"] += 1
print("  style tiêu đề:", counts)

# xoá nội dung mục lục cũ (giữ dòng tiêu đề MỤC LỤC)
dm = next(i for i, p in enumerate(doc.paragraphs) if p.text.strip().startswith("DANH MỤC THUẬT NGỮ"))
removed = 0
for i in range(dm - 1, toc_start, -1):
    t = doc.paragraphs[i].text.strip()
    if re.search(r"\.{4,}\s*\d*$", t) or t.startswith("Bấm chuột phải"):
        doc.paragraphs[i]._element.getparent().remove(doc.paragraphs[i]._element)
        removed += 1
print("  dòng mục lục cũ đã bỏ:", removed)
doc.save(str(DOC))

print("\n  Hình còn lại trong báo cáo:")
d2 = Document(str(DOC))
from docx.oxml.ns import qn
for n, shape in enumerate(d2.inline_shapes, 1):
    # tìm đoạn chứa hình để đoán ngữ cảnh
    rid = None
    print(f"   hình {n}: {shape.width.cm:.1f} x {shape.height.cm:.1f} cm")

# chèn mục lục thật bằng Word
w = win32.Dispatch("Word.Application")
w.Visible = False
d = w.Documents.Open(str(DOC))
rng = d.Content
rng.Find.ClearFormatting()
if rng.Find.Execute("MỤC LỤC"):
    rng.Collapse(0)  # về cuối đoạn tiêu đề
    toc = d.TablesOfContents.Add(Range=rng, UseHeadingStyles=True, LowerHeadingLevel=3,
                                 IncludePageNumbers=True, RightAlignPageNumbers=True)
    toc.Update()
    d.Save()
    print("  đã chèn mục lục tự động")
else:
    print("  !! không tìm thấy dòng MỤC LỤC")
d.Close(True)
w.Quit()

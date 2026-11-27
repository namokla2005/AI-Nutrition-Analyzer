"""Sửa các chỗ dấu phân cách bị đổi sai trong lần cập nhật vừa rồi (dấu phẩy -> dấu chấm)."""
from __future__ import annotations

import pathlib

from docx import Document

DOC = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\TTNT-Nam-Xuân Hải.docx")
doc = Document(str(DOC))

FIXES = [
    ("1.768 train. 383 validation. 373 test", "1.768 train, 383 validation, 373 test"),
    ("2.524 ảnh. chia 1.768 train. 383 validation và 373 test.",
     "2.524 ảnh, chia 1.768 train, 383 validation và 373 test."),
    ("v9 dùng 35 epoch. dừng sớm ở epoch 24. đạt accuracy test 0.7024 và macro F1 0.6745 trong 899.4 giây",
     "v9 dùng 35 epoch, dừng sớm ở epoch 24, đạt accuracy test 0,7024 và macro F1 0,6745 trong 899,4 giây"),
    ("accuracy test 0.7185 và macro F1 0.6917", "accuracy test 0,7185 và macro F1 0,6917"),
    ("trong 2.228.3 giây", "trong 2.228,3 giây"),
    ("trong 2228.3 giây", "trong 2.228,3 giây"),
    ("2.228.3", "2.228,3"),
]
done = []
for p in doc.paragraphs:
    for old, new in FIXES:
        if old not in p.text:
            continue
        replaced = False
        for run in p.runs:
            if old in run.text:
                run.text = run.text.replace(old, new)
                replaced = True
        if not replaced and p.runs:
            full = p.text.replace(old, new)
            p.runs[0].text = full
            for run in p.runs[1:]:
                run.text = ""
        done.append(old[:50])

doc.save(str(DOC))
print("  đã sửa:", len(done), "chỗ")
for item in done:
    print("   -", item)

# quét lại xem còn dấu sai nào
import re
left = []
doc2 = Document(str(DOC))
for i, p in enumerate(doc2.paragraphs):
    t = p.text
    if re.search(r"\d\.\d{4}", t) or re.search(r"(train|validation|test)\.\s+\d", t) or "epoch. dừng" in t:
        left.append((i, t[:160]))
print("\n  còn lại cần xem:", len(left))
for i, t in left:
    print(f"   [{i}] {t}")

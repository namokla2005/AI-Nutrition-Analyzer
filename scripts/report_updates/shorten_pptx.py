"""Thu gọn slide: giữ 25 slide thiết yếu, bỏ phần còn lại."""
from __future__ import annotations

import pathlib

from pptx import Presentation

PPT = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\TTNT-Nam-Xuân Hải.pptx")
KEEP = [1, 2, 4, 5, 9, 10, 11, 12, 13, 14, 15, 16, 19, 20, 21, 22, 25, 31, 32, 33, 35, 36, 39, 41, 43]

prs = Presentation(str(PPT))
total = len(prs.slides)
delete_zero_based = [i for i in range(total) if (i + 1) not in KEEP]
print(f"  trước: {total} slide | bỏ {len(delete_zero_based)} | giữ {len(KEEP)}")

xml_slides = prs.slides._sldIdLst
slides = list(xml_slides)
for idx in sorted(delete_zero_based, reverse=True):
    sld = slides[idx]
    rId = sld.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    prs.part.drop_rel(rId)
    xml_slides.remove(sld)

prs.save(str(PPT))
check = Presentation(str(PPT))
print(f"  sau: {len(check.slides)} slide")
for i, s in enumerate(check.slides, 1):
    texts = [sh.text_frame.text.strip().split("\n")[0][:46] for sh in s.shapes
             if sh.has_text_frame and sh.text_frame.text.strip()]
    title = texts[1] if len(texts) > 1 else (texts[0] if texts else "")
    print(f"   {i:>2}. {title}")

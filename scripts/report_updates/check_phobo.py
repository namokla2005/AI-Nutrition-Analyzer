import json, pathlib
from docx import Document
ROOT = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer")
meta = json.loads((ROOT / "models/image/latest.json").read_text(encoding="utf-8"))
per = {e["label"]: (e["support"], e["f1"]) for e in meta["metrics"]["test_per_class"]}
print("model đang phục vụ:", meta["num_classes"], "lớp | pho_bo:", per["pho_bo"], "| com_ga:", per["com_ga"])
# sửa 2 lỗi nhỏ trong đoạn 232
DOC = r"D:\Documents\BaoCao\TriTueNhanTao\TTNT-Nam-Xuân Hải.docx"
d = Document(DOC)
p = d.paragraphs[232]
raw = p.text
fixed = raw.replace("75,0%", "75,0 %").replace("80,7%", "80,7 %").replace("bộ nhớ), Ảnh", "bộ nhớ). Ảnh")
if fixed != raw:
    if p.runs:
        p.runs[0].text = fixed
        for r in p.runs[1:]:
            r.text = ""
    d.save(DOC)
    print("  đã sửa lỗi nhỏ")
print("CUỐI:", Document(DOC).paragraphs[232].text)

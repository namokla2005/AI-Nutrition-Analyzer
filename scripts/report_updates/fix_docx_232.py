import json, pathlib
from docx import Document
ROOT = pathlib.Path(r"D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer")
DOC = r"D:\Documents\BaoCao\TriTueNhanTao\TTNT-Nam-Xuân Hải.docx"
http = json.loads((ROOT / "data/reports/v10/http_verification.json").read_text(encoding="utf-8"))
meta = json.loads((ROOT / "models/image/latest.json").read_text(encoding="utf-8"))
f1 = {e["label"]: (e["f1"] or 0) for e in meta["metrics"]["test_per_class"]}
d = Document(DOC)
p = d.paragraphs[232]
print("TRƯỚC:", p.text)
new = (f"Kiểm chứng qua API thật với model v10 đang phục vụ, trên {http['stats']['n']} ảnh tập test "
       f"(2 ảnh mỗi lớp): top-1 {http['stats']['top1']}/{http['stats']['n']} = "
       f"{http['stats']['top1']/http['stats']['n']:.1%}".replace(".", ",") +
       f", top-3 {http['stats']['top3']}/{http['stats']['n']} = "
       f"{http['stats']['top3']/http['stats']['n']:.1%}".replace(".", ",") +
       f", thời gian trung bình {http['latency_ms_avg']:.0f} ms mỗi ảnh (lần gọi đầu mất khoảng 4,4 giây "
       f"do nạp model vào bộ nhớ). Ảnh pho_bo vẫn bị đoán sai — phù hợp với F1 "
       f"{f1['pho_bo']:.4f}".replace(".", ",") +
       "; lỗi tập trung ở các cặp món rất giống nhau (pho_bo, com_ga, xoi, banh_cuon, canh_chua).")
if p.runs:
    p.runs[0].text = new
    for r in p.runs[1:]:
        r.text = ""
else:
    p.add_run(new)
d.save(DOC)
print("SAU:", Document(DOC).paragraphs[232].text[:400])

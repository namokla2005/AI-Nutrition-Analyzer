from pptx import Presentation
PPT = r"D:\Documents\BaoCao\TriTueNhanTao\TTNT-Nam-Xuân Hải.pptx"
prs = Presentation(PPT)
s21 = prs.slides[20]

def set_text(shape, text):
    tf = shape.text_frame
    first = tf.paragraphs[0]
    if first.runs:
        first.runs[0].text = text
        for r in first.runs[1:]:
            r.text = ""
    else:
        first.text = text
    for extra in list(tf.paragraphs[1:]):
        extra._p.getparent().remove(extra._p)

def shape_of(slide, sid):
    return next((s for s in slide.shapes if s.shape_id == sid), None)

EDITS = {22: "66/88 = 75,0 %", 27: "71/88 = 80,7 %", 33: "4,4 s", 34: "lần đầu · nạp model"}
for sid, text in EDITS.items():
    s = shape_of(s21, sid)
    if s is not None:
        set_text(s, text)
prs.save(PPT)

prs2 = Presentation(PPT)
for sid in (11, 12, 13, 16, 17, 18, 21, 22, 23, 26, 27, 28, 31, 32, 33, 34, 35):
    s = shape_of(prs2.slides[20], sid)
    if s is not None:
        print(f"  {sid}: {s.text_frame.text[:90]}")

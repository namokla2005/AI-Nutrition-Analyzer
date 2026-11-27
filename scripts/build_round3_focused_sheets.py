#!/usr/bin/env python3
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageOps
P=Path(__file__).resolve().parents[1]; R=P/'data'/'raw'/'images'; O=P/'data'/'reports'/'round3_focused_sheets'; O.mkdir(parents=True,exist_ok=True)
terms={'goi_ga':{'chicken salad','Asian chicken salad','chicken cabbage salad'},'mi_xao':{'stir fried noodles','fried noodles','chow mein','yakisoba','lo mein'}}
for cls,queries in terms.items():
 paths=[]
 for s in (R/cls).glob('*.json'):
  try:
   if json.loads(s.read_text(encoding='utf-8')).get('query') in queries and s.with_suffix('.jpg').exists(): paths.append(s.with_suffix('.jpg'))
  except Exception: pass
 paths=sorted(paths)
 for old in O.glob(cls+'_*.jpg'): old.unlink()
 for pn,start in enumerate(range(0,len(paths),25),1):
  page=paths[start:start+25]; sh=Image.new('RGB',(1100,((len(page)+4)//5)*175),'white'); d=ImageDraw.Draw(sh)
  for i,p in enumerate(page):
   with Image.open(p) as im: t=ImageOps.contain(im.convert('RGB'),(210,139))
   x,y=i%5*220,i//5*175; sh.paste(t,(x+(220-t.width)//2,y+2)); d.text((x+4,y+145),f'{start+i+1:03d} {p.name}',fill='black')
  sh.save(O/f'{cls}_{pn:02d}.jpg',quality=92)
 print(cls,len(paths))

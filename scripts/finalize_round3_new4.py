#!/usr/bin/env python3
from pathlib import Path
import json,shutil,hashlib
from collections import Counter
from PIL import Image
P=Path(__file__).resolve().parents[1];R=P/'data'/'raw'/'images'; classes=['banh_da_cua','goi_ga','banh_trang_nuong','mi_xao']
accepted={
'banh_da_cua':{'commons_92984671.jpg','commons_92984676.jpg','commons_92984683.jpg','commons_92984684.jpg','ov_5b6a035d.jpg','web_057776e3.jpg','web_116b159e.jpg','web_1d569bc0.jpg','web_24374932.jpg','web_281dfde6.jpg','web_2e30aab8.jpg','web_311553b6.jpg','web_31fe4e1d.jpg','web_4519a6fe.jpg','web_46c542df.jpg','web_76a12bbf.jpg','web_7b9c2346.jpg','web_88250a11.jpg','web_9634c8e2.jpg','web_9b9eaccf.jpg','web_b4d77403.jpg','web_bdaa46d8.jpg','web_bff67541.jpg','web_c00dea00.jpg','web_cd5c072e.jpg','web_cdced75e.jpg','web_ce667237.jpg','web_cfcc1760.jpg','web_e2a7e3ae.jpg','web_e64e1793.jpg','web_ef468101.jpg','web_effbfc75.jpg','web_f2f8dde0.jpg','web_f44e6c2e.jpg','web_fbd199fa.jpg'},
'banh_trang_nuong':{'commons_29118319.jpg','commons_29118320.jpg','commons_29118321.jpg','commons_29118322.jpg','web_04a89e44.jpg','web_269a802d.jpg','web_518e69dd.jpg','web_62edbc9a.jpg','web_64d0c1f3.jpg','web_68e6946f.jpg','web_7130f473.jpg','web_7cea27e5.jpg','web_7d2f38c1.jpg','web_9f5878fb.jpg','web_a08985d3.jpg','web_a112d642.jpg','web_aba36f70.jpg','web_bd40500e.jpg','web_c247c3f9.jpg','web_ceeafe3c.jpg','web_ee26586b.jpg','web_fd23739b.jpg'},
'goi_ga':set(),'mi_xao':set()}
queries={'goi_ga':{'chicken salad','Asian chicken salad','chicken cabbage salad'},'mi_xao':{'stir fried noodles','fried noodles','chow mein','yakisoba','lo mein'}}
accept_idx={'goi_ga':{1,2,3,4,5,6,8,9,10,11,12,13,16,18,19,20,22,24,26,27,28,29,31,32,33,35,36,37,38,40,41,42,43,44,45,48,49,50,51,52,53,54,55},'mi_xao':set(range(1,56))-{1,11,13,14,15,16,17,18,27,37,39,43,46,49,50,53,55}}
for cls in ('goi_ga','mi_xao'):
 paths=[]
 for s in (R/cls).glob('*.json'):
  try:
   if json.loads(s.read_text(encoding='utf-8')).get('query') in queries[cls] and s.with_suffix('.jpg').exists():paths.append(s.with_suffix('.jpg'))
  except Exception:pass
 for i,p in enumerate(sorted(paths),1):
  if i in accept_idx[cls]:accepted[cls].add(p.name)
rows=[];summary=[]
for cls in classes:
 active=R/cls;rej=R/'_rejected'/cls;rej.mkdir(parents=True,exist_ok=True)
 all_images=list(active.glob('*.jpg'))+list(rej.glob('*.jpg'))
 for image in list(active.glob('*.jpg')):
  if image.name not in accepted[cls]:
   shutil.move(str(image),rej/image.name); side=image.with_suffix('.json')
   if side.exists():shutil.move(str(side),rej/side.name)
 for status,folder in [('accepted',active),('rejected',rej)]:
  for image in sorted(folder.glob('*.jpg')):
   side=image.with_suffix('.json'); data=json.loads(side.read_text(encoding='utf-8')) if side.exists() else {}
   data['review_status']=status; data['our_class']=cls; data['sha256']=hashlib.sha256(image.read_bytes()).hexdigest()
   with Image.open(image) as im:data['width'],data['height']=im.size
   side.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
   row={k:data.get(k) for k in ['id','title','url','foreign_landing_url','creator','license','license_url','provider','source','width','height','sha256','our_class','query','review_status']};row['local_file']=image.relative_to(P).as_posix();rows.append(row)
 a=len(list(active.glob('*.jpg')));x=len(list(rej.glob('*.jpg')));summary.append({'class':cls,'downloaded':a+x,'rejected':x,'accepted':a,'clean_total':a,'missing_to_34':max(0,34-a)})
out=P/'data'/'reports'/'round3_provenance_new4.json';out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report={'classes':summary,'provenance_path':out.relative_to(P).as_posix(),'provenance_records':len(rows),'license_counts':dict(Counter((r.get('license') or 'unknown') for r in rows)),'missing_files':sum(not (P/r['local_file']).exists() for r in rows)}
(P/'data'/'reports'/'round3_collection_summary_new4.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))

from pathlib import Path
import sys,json,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image
from session_reader import ocr_rows
from training_model import character_reading
from leveling import bar_numbers
cases=[];failures=[]
for name,lv,n in [('live_exp_2560.png',26,29285),('live_frame_ant_tunnel2.png',25,5299),('live_frame_1920.png',25,5340)]:
 im=Image.open(root/'tests'/name).convert('RGB');w,h=im.size;footer=im.crop((int(w*.1),int(h*.91),int(w*.92),h));footer.thumbnail((1800,300))
 rows=ocr_rows(footer,max_size=(1800,300));selected=[row for row in rows if 'exp' in row[1].casefold() and '%' in row[1]]
 assert selected,(name,[text for box,text,score in rows])
 box,text,score=selected[0];x0=max(0,int(min(p[0] for p in box))-3);x1=min(footer.width,int(max(p[0] for p in box))+3);y0=max(0,int(min(p[1] for p in box))-3);y1=min(footer.height,int(max(p[1] for p in box))+3);strip=footer.crop((x0,y0,x1,y1))
 for mode,fraction in [('integer_side',.5),('integer_side',.6),('percent_side',.5),('percent_side',.6)]:
  split=int(strip.width*fraction);piece=strip.crop((0,0,split,strip.height)) if mode=='integer_side' else strip.crop((split,0,strip.width,strip.height))
  raw=ocr_rows(piece,max_size=(1800,300));texts=[t for box,t,score in raw if score>=.75];reading=character_reading(texts)
  numbers,pcts,_=bar_numbers([t for t in texts if 'exp' in t.casefold() or '%' in t]);missing=not numbers or not pcts
  c=dict(fixture=name,mode=mode,split_fraction=fraction,texts=texts,numbers=numbers,pcts=pcts,reading=reading,concordant_channel_missing=missing);cases.append(c)
  if reading and (missing or (reading['level'],reading['exp'])!=(lv,n)):failures.append(c)
report=dict(ok=not failures,cases=cases,failures=failures,missing_component_cases=sum(c['concordant_channel_missing'] for c in cases),source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='ActualOCR ofpartialEXPtextboxes from3localHUDfooters,productionconfidencefilter+characterparser; missingintegerorpercent mustnotyieldacceptedreading; no livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],cases=len(cases),missing_component_cases=report['missing_component_cases'],failures=failures)))

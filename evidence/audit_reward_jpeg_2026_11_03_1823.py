from pathlib import Path
import sys,io,json,hashlib
from collections import Counter
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image
import session_reader as reader
cases=[];failures=[]
for name in ('session-rewards-fixture.png','party-rewards-fixture.png'):
 im=Image.open(root/'tests'/name).convert('RGB')
 truth=Counter([('mesos',8),('mesos',10),('mesos',7),('mesos',10),('exp',7),('bonus',2)]) if name.startswith('session') else Counter([('exp',7),('bonus',2)]*3)
 for quality in (95,80,60,35):
  buffer=io.BytesIO();im.save(buffer,format='JPEG',quality=quality);buffer.seek(0)
  image=Image.open(buffer).convert('RGB');reader._money_retry_turn=0
  events=reader.read_reward_image(image,True);known=Counter(row for row in events if row[1] is not None)
  wrong=list((known-truth).elements());missing=list((truth-known).elements())
  case=dict(fixture=name,jpeg_quality=quality,events=list(events),positions=events.positions,trusted_money=sorted(events.trusted_money),wrong=wrong,missing=missing)
  cases.append(case)
  if wrong:failures.append(case)
report=dict(ok=not failures,cases=cases,failures=failures,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Actual local reward OCR after in-memory JPEG95/80/60/35; manually established original notice values, unknown/missing reported, no live game or source image overwrite')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],cases=len(cases),wrong_cases=len(failures),missing_counts=[len(c['missing']) for c in cases])))

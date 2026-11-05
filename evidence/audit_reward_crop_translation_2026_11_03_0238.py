from pathlib import Path
import sys,json,hashlib
from collections import Counter
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image,ImageOps
import session_reader as reader
cases=[];unexpected=[]
for name in ('session-rewards-fixture.png','party-rewards-fixture.png'):
 im=Image.open(root/'tests'/name).convert('RGB');reader._money_retry_turn=0
 baseline=reader.read_reward_image(im.copy(),True);expected=Counter(e for e in baseline if e[1] is not None)
 for left,top in ((0,0),(1,0),(0,1),(2,3),(3,2),(4,4),(8,4),(4,8),(12,12)):
  image=ImageOps.expand(im,border=(left,top,12-left,12-top),fill=(0,0,0));reader._money_retry_turn=0
  events=reader.read_reward_image(image,True);known=Counter(e for e in events if e[1] is not None)
  extra=list((known-expected).elements());missing=list((expected-known).elements())
  case=dict(fixture=name,padding=[left,top],events=list(events),unexpected_vs_baseline=extra,missing_vs_baseline=missing);cases.append(case)
  if extra:unexpected.append(case)
report=dict(ok=not unexpected,cases=cases,unexpected=unexpected,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Recorded reward images with translation via constant12pixelborder, identical pixels/content; compare concrete amounts against same-image baseline, missing rows explicit; no livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],cases=len(cases),unexpected=unexpected,missing_cases=sum(bool(c['missing_vs_baseline']) for c in cases))))

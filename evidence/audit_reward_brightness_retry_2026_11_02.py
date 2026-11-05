from pathlib import Path
import sys,json,hashlib
from collections import Counter
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image,ImageEnhance
from session_reader import read_reward_image
cases=[];failures=[]
for name in ('session-rewards-fixture.png','party-rewards-fixture.png'):
 image=Image.open(root/'tests'/name).convert('RGB')
 baseline=list(read_reward_image(image.copy(),True));expected=Counter(row for row in baseline if row[1] is not None)
 for factor in (.65,.8,1.0,1.2,1.4):
  events=read_reward_image(ImageEnhance.Brightness(image).enhance(factor),True)
  known=Counter(row for row in events if row[1] is not None)
  wrong=list((known-expected).elements());missing=list((expected-known).elements())
  case=dict(fixture=name,brightness=factor,events=list(events),trusted_money=sorted(events.trusted_money),unexpected=wrong,missing=missing)
  cases.append(case)
  if wrong:failures.append(case)
report=dict(ok=not failures,cases=cases,failures=failures,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Local supplied reward fixtures with synthetic brightness changes; missing rows reported, not inferred; no live gameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],cases=len(cases),failures=failures)))

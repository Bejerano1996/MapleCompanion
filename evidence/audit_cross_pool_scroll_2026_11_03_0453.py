from pathlib import Path
import sys,json,random,hashlib,statistics
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from session_rewards import RewardTracker
from session_reader import RewardRead
b=Path(__file__).resolve().parent;old=json.loads((b/'audit_frozen_static_ocr_3_24.json').read_text());bright=json.loads((b/'audit_frozen_money_brightness_3_24.json').read_text());sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest();assert old['source_sha']==bright['source_sha']==sha
cases=0;polls=0;under=[];over=[]
for name in old['captures']:
 pool=old['captures'][name]+bright['captures'][name]
 for seed in range(250):
  r=random.Random(seed);tracker=RewardTracker(confirm_money=2);totals=dict(exp=0,kills=0,party_exp=0,mesos=0)
  for frame in range(60):
   c=r.choice(pool);events=list(c['events']);positions=list(c['positions']);trusted=list(c['trusted_money'])
   if frame>=10:
    last=positions[-1][0];positions += [(last+60,45),(last+120,45),(last+180,45)]
    amount=None if frame<56 and r.random()<.35 else 17
    events += [('exp',13),('bonus',3),('mesos',amount)]
   if frame>=10:
    gaps=[b[0]-a[0] for a,b in zip(c['positions'],c['positions'][1:])];gap=statistics.median(gaps)
    # Synthetic append scrolls three rows; preserve actual old OCR coordinates.
    last=c['positions'][-1][0];positions=list(c['positions'])+[(last+gap*(j+1),45) for j in range(3)]
    entries=[(event,(p[0]-3*gap,p[1])) for event,p in zip(events,positions) if p[0]-3*gap>=0]
    events=[e for e,p in entries];positions=[p for e,p in entries];trusted=[]
   reading=RewardRead(events,False,trusted,positions);delta=tracker.feed(reading);polls+=1
   for key in totals:totals[key]+=delta[key]
   if frame<10:assert not any(totals.values()),(name,seed,frame,totals)
   if any(totals[k]>v for k,v in dict(exp=16,kills=1,party_exp=3,mesos=17).items()):over.append(dict(fixture=name,seed=seed,frame=frame,totals=dict(totals)));break
  if totals!=dict(exp=16,kills=1,party_exp=3,mesos=17):under.append(dict(fixture=name,seed=seed,totals=totals))
  cases+=1
report=dict(ok=not over,cases=cases,polls=polls,overcounts=over,under_or_inexact=under,source_sha=sha,scope='Actual cached30OCRvariants plus synthetic3rowupwardscroll/croppedoldrows/new13EXP3bonus17money,unknownmoneyphases. Safetybound vs truegains, missingcountsreported; no appendedpixelsOCR/livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],cases=cases,polls=polls,overcounts=len(over),under_or_inexact=len(under),examples=over[:2]+under[:2])))

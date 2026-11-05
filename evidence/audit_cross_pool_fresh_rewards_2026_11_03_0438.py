from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from session_rewards import RewardTracker
from session_reader import RewardRead
b=Path(__file__).resolve().parent;old=json.loads((b/'audit_frozen_static_ocr_3_24.json').read_text());bright=json.loads((b/'audit_frozen_money_brightness_3_24.json').read_text());sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest();assert old['source_sha']==bright['source_sha']==sha
cases=0;polls=0
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
   reading=RewardRead(events,False,trusted,positions);delta=tracker.feed(reading);polls+=1
   for key in totals:totals[key]+=delta[key]
   if frame<10:assert not any(totals.values()),(name,seed,frame,totals)
   assert all(totals[k]<=v for k,v in dict(exp=16,kills=1,party_exp=3,mesos=17).items()),(name,seed,frame,totals)
  assert totals==dict(exp=16,kills=1,party_exp=3,mesos=17),(name,seed,totals)
  cases+=1
report=dict(ok=True,cases=cases,polls=polls,source_sha=sha,scope='Cached actual30OCRvariants as old baseline, synthetic appended13EXP/3party/17money with35percent unknownamount phases and moving positions; finalfreshrewardscountedonce. No appendedpixelsOCRed/no livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

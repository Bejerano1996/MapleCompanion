from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from session_reader import RewardRead
from session_rewards import RewardTracker
failures=[];cases=0
for n in (6,8,12):
 for seed in range(100):
  rng=random.Random(seed);values=[10 if i%2==0 else 20 for i in range(n)];positions=[(20*i,12) for i in range(n)]
  tracker=RewardTracker(confirm_money=2);frames=[];total=0
  for frame in range(20):
   events=[('mesos',v if rng.random()<.45 else None) for v in values];frames.append(events)
   delta=tracker.feed(RewardRead(events,False,(),positions));total+=delta['mesos']
   if total:
    failures.append(dict(rows=n,seed=seed,frame=frame,total=total,events=frames));break
  cases+=1
report=dict(ok=not failures,cases=cases,failures=failures,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic stationary pre-session alternating10/20mesosrows with partial OCR changes; no new rewards and no livegameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],cases=cases,failures=len(failures),example=failures[:1])))

from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from session_reader import RewardRead
from session_rewards import RewardTracker
failures=[];cases=0
for n in (6,12):
 for seed in range(100):
  rng=random.Random(seed);values=[10,20,30]*(n//3);t=RewardTracker(confirm_money=2);history=[];total=0
  # All initial notices predate the session, with known geometry.
  t.feed(RewardRead([('mesos',v) for v in values],False,(),[(20*i,12) for i in range(n)]))
  for frame in range(15):
   visible=[i for i in range(n) if rng.random()>.25];events=[('mesos',values[i]) for i in visible];positions=[(20*i,12) for i in visible]
   history.append(dict(indices=visible,events=events));total+=t.feed(RewardRead(events,True,(),positions))['mesos']
   if total:
    failures.append(dict(rows=n,seed=seed,frame=frame,total=total,history=history));break
  cases+=1
report=dict(ok=not failures,cases=cases,failures=failures,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic pre-session stationary money rows,whole-row partial masking/dropout and recovery,no actualpickups or livegameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],cases=cases,failures=len(failures),example={k:v for k,v in failures[0].items() if k!='history'} if failures else None)))

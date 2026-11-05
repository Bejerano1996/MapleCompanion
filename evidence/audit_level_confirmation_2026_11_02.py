import sys,json,random,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_accounting import TrainingAccountant
from session_rewards import session_token
checks=0
for seed in range(200):
 rng=random.Random(seed);s=dict(id='probe',running_since=1,exp=0,mesos=0,kills=0,auto_rewards=True)
 a=TrainingAccountant();token=session_token(s);a.feed(s,token,[],{'level':27,'exp':1000},0);a.feed(s,token,[],{'level':27,'exp':1000},1)
 at=1;current=1000
 for n in range(20):
  at+=rng.uniform(.15,3);bad={'level':rng.choice([25,30]),'exp':100}
  a.feed(s,token,[],bad,at)
  assert s['exp']==current-1000,(seed,n,'outlier',s)
  at+=rng.uniform(.15,3);current+=rng.randint(1,20)
  a.feed(s,token,[],{'level':27,'exp':current},at)
  assert s['exp']==current-1000,(seed,n,'valid',s)
  checks+=2
sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest()
report=dict(ok=True,seeds=200,assertions=checks,source_sha=sha,method='Synthetic interleaved level outliers and valid HUD readings; no live gameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

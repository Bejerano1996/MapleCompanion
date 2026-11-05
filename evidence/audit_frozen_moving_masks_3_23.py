from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from session_reader import RewardRead
from session_rewards import RewardTracker
failures=[];cases=0;max_rows=0;partial_under=0
for seed in range(200):
 rng=random.Random(seed);rows=[('exp',7),('bonus',2),('mesos',10),('exp',7),('bonus',2),('mesos',20)]*2
 t=RewardTracker(confirm_money=2);positions=lambda:[(20*i,12) for i in range(len(rows))]
 t.feed(RewardRead(rows,False,(),positions()));observed=dict(exp=0,mesos=0);truth=dict(exp=0,mesos=0);history=[]
 for frame in range(100):
  if frame>=20 and rng.random()<.3:
   amount=rng.choice([100,200,300]);rows=(rows+[('exp',7),('bonus',2),('mesos',amount)])[-12:];truth['exp']+=9;truth['mesos']+=amount
  partial=rng.random()<.75
  start=rng.randrange(len(rows));length=rng.randint(1,5)
  visible=[i for i in range(len(rows)) if not partial or not start<=i<start+length]
  events=[rows[i] for i in visible];pos=[(20*i,12) for i in visible]
  delta=t.feed(RewardRead(events,partial,(),pos))
  for kind in observed:observed[kind]+=delta[kind]
  max_rows=max(max_rows,len(t.previous or []));history.append(dict(frame=frame,visible=visible,partial=partial,delta=delta,observed=dict(observed),truth=dict(truth)))
  if observed['exp']>truth['exp'] or observed['mesos']>truth['mesos']:
   failures.append(dict(seed=seed,frame=frame,history=history));break
  assert len(t.previous or [])<=128
 if observed['mesos']<truth['mesos']:partial_under+=1
 cases+=1
report=dict(ok=not failures,cases=cases,failures=failures,max_retained_rows=max_rows,partial_undercount_streams=partial_under,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic actual append/scroll plus changing contiguous masks; safety compares aggregate observed<=actualnew rewards,unseenrewardundercountallowed; no livegameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],cases=cases,failures=len(failures),max_rows=max_rows,example=dict(seed=failures[0]['seed'],last=failures[0]['history'][-1]) if failures else None)))

from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from session_reader import RewardRead
from session_rewards import RewardTracker
failures=[];cases=0;missed=0;max_rows=0
for seed in range(100):
 rng=random.Random(seed);rows=[('exp',7,None),('bonus',2,None),('mesos',1,None)]*4;t=RewardTracker(confirm_money=2);seen=set();created=0
 def observation(partial):
  start=rng.randrange(len(rows));length=rng.randint(1,5)
  visible=[i for i in range(len(rows)) if not partial or not start<=i<start+length]
  return RewardRead([(rows[i][0],rows[i][1]) for i in visible],partial,(),[(20*i,12) for i in visible]),{rows[i][2] for i in visible if rows[i][0]=='mesos' and rows[i][2] is not None}
 t.feed(observation(False)[0])
 for frame in range(143):
  if frame in range(20,60,5):
   identity=created;created+=1;rows=(rows+[('exp',7,None),('bonus',2,None),('mesos',10*8**identity,identity)])[-12:]
  events,visible_ids=observation(frame<140 and rng.random()<.75);delta=t.feed(events)['mesos'];max_rows=max(max_rows,len(t.previous or []))
  if delta%10:
   failures.append(dict(seed=seed,frame=frame,reason='baseline_money',delta=delta));break
  number=delta//10;credited=set();index=0;invalid=False
  while number:
   digit=number%8;number//=8
   if digit>1 or digit and (index in seen or index not in visible_ids):invalid=True
   if digit:credited.add(index)
   index+=1
  if invalid:
   failures.append(dict(seed=seed,frame=frame,reason='duplicate_or_unobserved_pickup',delta=delta,seen=sorted(seen),visible=sorted(visible_ids)));break
  seen.update(credited)
  assert len(t.previous or [])<=128
  if frame>=140:assert len(t.previous)==len(rows) and not t.was_partial
 missed+=created-len(seen);cases+=1
report=dict(ok=not failures,cases=cases,failures=failures,unseen_or_unconfirmed_pickups=missed,max_rows=max_rows,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic8unique base8encodedmoneyamounts under100million perstream; per-frame decoded identities exclude duplicates/pre-sessioncoins,real append/scroll and contiguousmaskchanges; no livegameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],cases=cases,failures=len(failures),missed=missed,max_rows=max_rows,examples=failures[:3])))

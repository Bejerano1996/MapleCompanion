import sys,json,random,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from session_rewards import RewardTracker
checks=0
for seed in range(200):
 rng=random.Random(seed);tracker=RewardTracker(confirm_money=2);rows=[('mesos',None)];tracker.feed(rows)
 total=0;expected=0
 # An unread pre-session amount must not become a new pickup.
 rows=[('mesos',rng.randint(1,1000))]
 for _ in range(3):total+=tracker.feed(rows)['mesos']
 assert total==0
 for index in range(20):
  amount=rng.randint(1,1000);expected+=amount
  rows=rows[-3:]+[('exp',1000+index),('mesos',None)]
  for _ in range(rng.randint(1,4)):total+=tracker.feed(rows)['mesos']
  # EXP can appear while the new money amount remains unreadable.
  if rng.choice((False,True)):
   rows.append(('exp',2000+index));total+=tracker.feed(rows)['mesos']
   money_index=len(rows)-2
  else:money_index=len(rows)-1
  rows[money_index]=('mesos',amount)
  for _ in range(rng.randint(2,5)):total+=tracker.feed(rows)['mesos']
  assert total==expected,(seed,index,total,expected,rows)
  checks+=1
report=dict(ok=True,seeds=200,pickups=checks,scope='Synthetic stable anchored notice rows, unknown amounts, later refinement and intervening EXP; no live gameplay',source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest())
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

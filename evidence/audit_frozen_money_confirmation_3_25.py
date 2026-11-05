from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from session_rewards import RewardTracker,reward_event,reward_kind
r=random.Random(353);cases=0
for i in range(1000):
 prefix=r.choice(('have gaired mesos','have laired mesos','You have gained mesos'));coin=r.randint(1,100000)
 tracker=RewardTracker(confirm_money=2);old=[('exp',7),('bonus',2),('mesos',10)];tracker.feed(old)
 unknown=prefix+' (+?)';assert reward_event(unknown) is None and reward_kind(unknown)=='mesos'
 assert tracker.feed(old+[('mesos',None)])['mesos']==0
 event=reward_event(prefix+' (+'+str(coin)+')');assert event==('mesos',coin)
 assert tracker.feed(old+[event])['mesos']==0
 assert tracker.feed(old+[event])['mesos']==coin
 assert tracker.feed(old+[event])['mesos']==0
 for tail in (' (+1,,000)',' (+0)',' (+-10)',' (+?)'):
  assert reward_event(prefix+tail) is None
 assert reward_event(prefix+' (+10) You rerelved EXP (+7)') is None
 cases+=1
report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic observedmoney-prefixvariants:unknownamountpending,tworeadconfirmation,newpickupcreditedonce,malformed/zero/negative/mergedrejection; no liveOCR/game')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

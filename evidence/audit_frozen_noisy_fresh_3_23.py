from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from session_rewards import RewardTracker,reward_event,reward_kind
from session_reader import RewardRead
saved=json.loads((Path(__file__).parent/'audit_static_ocr_timeline_after_2026_11_03_0253.json').read_text());r=random.Random(308);cases=0
for name,captures in saved['captures'].items():
 for i in range(100):
  c=r.choice(captures);old=RewardRead(c['events'],False,c['trusted_money'],c['positions']);tracker=RewardTracker(confirm_money=2)
  tracker.feed(old);assert not any(tracker.feed(old).values())
  texts=['You receved EXP (+11)','Borus EXP for PAFTY (+3)','You have qained mesos (+17)'];fresh=[reward_event(t) for t in texts];assert all(fresh)
  positions=list(old.positions);last=positions[-1][0] if positions else 0
  positions += [(last+60*(j+1),45) for j in range(3)]
  events=RewardRead(list(old)+fresh,False,(),positions);total=dict(exp=0,kills=0,party_exp=0,mesos=0)
  for _ in range(3):
   d=tracker.feed(events)
   for k in total:total[k]+=d[k]
  assert total==dict(exp=14,kills=1,party_exp=3,mesos=17),(name,i,total)
  cases+=1
prefixes=('You receved EXP','Borus EXP for PAFTY','You have qained mesos');merged=0
for i in range(1000):
 text=r.choice(prefixes)+' (+'+str(r.randint(1,100000))+') '+r.choice(prefixes)+' (+'+str(r.randint(1,100000))+')'
 assert reward_event(text) is None,text;merged+=1
report=dict(ok=True,fresh_reward_cases=cases,merged_rejections=merged,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Cached actualOCRbaseline+synthetic parsed new append/positions,200freshrewards;1000mergednoisy-prefixrejections; no new imageOCR/livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

from pathlib import Path
import sys,json,hashlib,random
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from session_reader import RewardRead
from session_rewards import RewardTracker
source=Path(__file__).with_name('audit_reward_jpeg_2026_11_03_1823.json');data=json.loads(source.read_text());cases=0;polls=0;failures=[]
for fixture in ('session-rewards-fixture.png','party-rewards-fixture.png'):
 rows=[r for r in data['cases'] if r['fixture']==fixture]
 pool=[RewardRead(r['events'],False,r['trusted_money'],r['positions']) for r in rows]
 for seed in range(100):
  rng=random.Random(seed);order=[rng.randrange(4) for _ in range(100)];tracker=RewardTracker(confirm_money=2);tracker.feed(pool[order[0]])
  for frame,index in enumerate(order[1:],1):
   delta=tracker.feed(pool[index]);polls+=1
   if any(delta.values()):
    failures.append(dict(fixture=fixture,seed=seed,frame=frame,delta=delta,order=order[:frame+1],recent_qualities=[rows[i]['jpeg_quality'] for i in order[max(0,frame-6):frame+1]]));break
  cases+=1
report=dict(ok=not failures,streams=cases,polls=polls,failures=failures,cached_ocr_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic unchanged-old-image sequence replay of cached actual JPEG OCR; quality varies independently eachpoll, unlike native uncompressed capture. Anycredit is a stress falsepositive, not livegame evidence.')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],streams=cases,polls=polls,false_credit_streams=len(failures),examples=failures[:2])))

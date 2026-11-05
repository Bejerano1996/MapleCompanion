from pathlib import Path
import sys,json,random,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image
import session_reader as reader
from session_rewards import RewardTracker
cases=0;polls=0
for n in range(2,7):
 for seed in range(40):
  rng=random.Random(seed*10+n);values=([23]*n if seed%2 else rng.sample(range(1,100),n));tracker=RewardTracker(confirm_money=2);tracker.feed([]);total=0
  image=Image.new('RGB',(300,200))
  def recover(image,pos):return values[round((pos[0]-16)/20)]
  with patch.object(reader,'_money_retry_turn',rng.randrange(12)),patch.object(reader,'retry_money_row',side_effect=recover) as retry:
   for frame in range(25):
    rows=[]
    for index,amount in enumerate(values):
     y=10+20*index;known=frame>=20 or rng.random()<.4
     rows.append(([[0,y],[100,y],[100,y+12],[0,y+12]],'You have gained mesos (+'+(str(amount) if known else '?')+')',.90))
    before=retry.call_count
    with patch.object(reader,'ocr_rows',return_value=rows):events=reader.read_reward_image(image,True)
    assert retry.call_count-before<=1
    total+=tracker.feed(events)['mesos'];assert total<=sum(values),(n,seed,frame,total,values)
    polls+=1
   assert total==sum(values),(n,seed,total,values)
  cases+=1
report=dict(ok=True,cases=cases,polls=polls,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic stationary2-6money rows with changing known/pending subset,distinct/repeatedvalues,finalstableknownreadings; no game capture')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

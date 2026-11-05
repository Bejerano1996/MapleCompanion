from pathlib import Path
import sys,json,random,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image
import session_reader as reader
from session_rewards import RewardTracker
cases=0;ambiguous=[]
for n in range(2,7):
 for phase in range(2*n):
  for blocked in (False,True):
   for repeated in (False,True):
    rng=random.Random(n*100+phase);values=([23]*n if repeated else rng.sample(range(1,100),n))
    rows=[([[0,y],[100,y],[100,y+12],[0,y+12]],'You have gained mesos (+?)',.9) for y in range(10,10+20*n,20)]
    def recover(image,pos):
     index=round((pos[0]-16)/20)
     return None if blocked and index==0 else values[index]
    tracker=RewardTracker(confirm_money=2);tracker.feed([]);total=0
    with patch.object(reader,'_money_retry_turn',phase),patch.object(reader,'ocr_rows',return_value=rows),patch.object(reader,'retry_money_row',side_effect=recover) as retry:
     for _ in range(6*n+4):total+=tracker.feed(reader.read_reward_image(Image.new('RGB',(300,200)),True))['mesos']
     expected=sum(values[1:] if blocked else values)
     assert total<=expected,(n,phase,blocked,total,values)
     if not repeated:assert total==expected,(n,phase,blocked,total,values)
     elif total<expected:ambiguous.append(dict(rows=n,phase=phase,blocked=blocked,observed=total,reference=expected))
     assert retry.call_count==6*n+4
    cases+=1
report=dict(ok=True,cases=cases,ambiguous_incomplete=ambiguous,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic fixed row geometry,2-6pending money rows,all scheduler phases,optional unreadablefirstrow; no live gameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

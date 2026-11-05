from pathlib import Path
import sys,json,random,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image
import session_reader as reader
from session_rewards import RewardTracker
rng=random.Random(1638);cases=0
for seed in range(100):
 value=rng.randint(1000,1000000)
 for score in (.8,.99):
  def read(amount,confidence):
   rows=[([[0,10],[280,10],[280,22],[0,22]],'You have gained mesos (+'+amount+')',confidence)]
   with patch.object(reader,'ocr_rows',return_value=rows),patch.object(reader,'retry_money_row',return_value=None):return reader.read_reward_image(Image.new('RGB',(300,100)),True)
  pending=read(f'{value:,},',.99);resolved=read(f'{value:,}',score)
  assert list(pending)==[('mesos',None)] and not pending.trusted_money
  t=RewardTracker(confirm_money=2);t.feed([]);total=0
  for events in [pending,pending,pending,resolved,resolved,pending,resolved,resolved]:total+=t.feed(events)['mesos']
  assert total==value,(seed,score,total,value)
  old=RewardTracker(confirm_money=2);old.feed(pending)
  assert sum(old.feed(events)['mesos'] for events in [resolved,resolved,pending,resolved])==0
  cases+=1
report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic malformedamount->pending->resolvedOCR->RewardTracker atweak/strongconfidence,baselineexclusionandredropouts; no realcapture')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

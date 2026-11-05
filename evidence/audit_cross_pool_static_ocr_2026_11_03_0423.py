from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from session_reader import RewardRead
from session_rewards import RewardTracker
base=Path(__file__).resolve().parent
old=json.loads((base/'audit_frozen_static_ocr_3_24.json').read_text());bright=json.loads((base/'audit_frozen_money_brightness_3_24.json').read_text())
sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest();assert old['source_sha']==bright['source_sha']==sha
failures=[];polls=0
for name in old['captures']:
 captures=old['captures'][name]+bright['captures'][name]
 reads=[RewardRead(c['events'],c.get('partial',False),c['trusted_money'],c['positions']) for c in captures]
 for seed in range(500):
  r=random.Random(seed);order=[r.randrange(len(reads)) for _ in range(100)];tracker=RewardTracker(confirm_money=2);tracker.feed(reads[order[0]])
  for index in order[1:]:
   delta=tracker.feed(reads[index]);polls+=1
   if any(delta.values()):failures.append(dict(fixture=name,seed=seed,delta=delta));break
report=dict(ok=not failures,streams=1000,polls=polls,cached_real_ocr_variants=30,failures=failures,source_sha=sha,scope='Cross-pool replay of current-release actualOCR18translation+12brightnessvariants; unchangedoldmessages, no new OCR/livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='failures'}));print(json.dumps(failures[:2]))

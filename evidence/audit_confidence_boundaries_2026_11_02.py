from pathlib import Path
import sys,json,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image
import session_reader as reader
cases=0
for prefix_score in (.8,.94,.99):
 for digit_score in (.7,.749999,.75,.9,.949999,.95,.99):
  for split in (False,True):
   for padding in (0,20,80):
    prefix='You have gained mesos'+' '*padding
    parts=[(prefix,prefix_score)] + ([('(+',.99),('1',digit_score),('7)',.99)] if split else [('(+17)',digit_score)])
    rows=[([[100*i,10],[100*i+90,10],[100*i+90,22],[100*i,22]],text,score) for i,(text,score) in enumerate(parts)]
    weighted=sum(len(t)*s for t,s in parts)/sum(len(t) for t,s in parts)
    accepted=weighted>=.75 and digit_score>=.75
    trusted=accepted and weighted>=.95 and digit_score>=.95
    with patch.object(reader,'ocr_rows',return_value=rows),patch.object(reader,'retry_money_row',return_value=None):events=reader.read_reward_image(Image.new('RGB',(500,100)),True)
    assert list(events)==[('mesos',17 if accepted else None)],(parts,list(events))
    assert bool(events.trusted_money)==trusted,(parts,events.trusted_money)
    cases+=1
report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic OCR confidence boundary/split-digit boxes; no actual OCR recognition or livegameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

from pathlib import Path
import sys,json,types,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_context import ContextTracker
from training_yield import YieldLearner
import training_ui
cases=[]
for before in range(2,7):
 for after in [None]+list(range(2,7)):
  if before==after:continue
  tracker=ContextTracker();read=lambda n:dict(game=True,map='a',mobs=[23],party_visible=n)
  tracker.feed(read(before),90);context=tracker.feed(read(before),98)
  a=types.SimpleNamespace(state=dict(training_auto_context=True,character_exp={'level':32,'exp':1000}),db=types.SimpleNamespace(monsters={23:dict(id=23,exp=50)},map_data={}),_training_context=context)
  for name in ('training_target','training_plausible_targets','training_gain_context'):
   setattr(a,name,types.MethodType(getattr(training_ui,name),a))
  learner=YieldLearner()
  with patch('time.time',return_value=100):
   key=a.training_gain_context()
   for t in (98,99,100):learner.observe(key,dict(exp=9,kills=1),9,t)
   assert learner.estimate(key,100)==9
   a._training_context=tracker.feed(read(after),100)
   assert a.training_gain_context()[2] is None
   assert learner.estimate(a.training_gain_context(),100) is None
   a._training_context=tracker.feed(read(after),108)
   assert a.training_gain_context()[2]==after
   assert learner.progress(a.training_gain_context(),108)==0
   # Returning to the original count must not resurrect its learned yield.
   tracker.feed(read(before),116);a._training_context=tracker.feed(read(before),124)
   assert learner.estimate(a.training_gain_context(),124) is None
  cases.append([before,after])
report=dict(ok=True,transitions=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic visible roster count transitions, not eligibility or member identity; no game capture')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=True,transitions=len(cases))))

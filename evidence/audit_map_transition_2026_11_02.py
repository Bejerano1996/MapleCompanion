from pathlib import Path
import sys,json,types,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_context import ContextTracker
from training_yield import YieldLearner
import training_ui
paths={'new_map':['b','b','a','a'],'unread_title':[None,'a','a'],'game_unavailable':['absent','a','a'],'flickering_titles':['b','a','b','a','a']}
results=[]
for label,path in paths.items():
 tracker=ContextTracker();reading=lambda location:dict(game=location!='absent',map=location if location!='absent' else None,mobs=[23],party_visible=4)
 tracker.feed(reading('a'),90);context=tracker.feed(reading('a'),98)
 a=types.SimpleNamespace(state=dict(training_auto_context=True,character_exp={'level':32,'exp':1000}),db=types.SimpleNamespace(monsters={23:dict(id=23,exp=50)},map_data={}),_training_context=context)
 for name in ('training_target','training_plausible_targets','training_gain_context'):
  setattr(a,name,types.MethodType(getattr(training_ui,name),a))
 learner=YieldLearner()
 with patch('time.time',return_value=100):
  key=a.training_gain_context()
  for t in (98,99,100):learner.observe(key,dict(exp=9,kills=1),9,t)
  learner.add_window(key,dict(exp=9,kills=1),100)
  assert learner.estimate(key,100)==9
  for i,location in enumerate(path):
   a._training_context=tracker.feed(reading(location),100+i)
   signature=a.training_gain_context()
   assert learner.estimate(signature,100+i) is None,(label,i,signature)
   assert learner.take_window(signature,100+i)=={},'Old calibration window crossed map transition'
  final=a.training_gain_context()
  for t in (110,111):learner.observe(final,dict(exp=9,kills=1),9,t)
  assert learner.estimate(final,111) is None
  learner.observe(final,dict(exp=9,kills=1),9,112)
  assert learner.estimate(final,112)==9
 results.append(dict(path=label,observations=len(path),fresh_samples_required=3))
report=dict(ok=True,results=results,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic ContextTracker-to-target-to-yield integration, not live gameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

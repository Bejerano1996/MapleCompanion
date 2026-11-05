from pathlib import Path
import sys,json,types,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import training_ui
from training_yield import YieldLearner
cases=[]
for initial in (True,False):
 for fresh in (True,False):
  a=types.SimpleNamespace(state=dict(training_auto_context=initial,training_target='23',map='a',party=2,character_exp={'level':27,'exp':1000},character_exp_at=100,training_personal_gain=None),db=types.SimpleNamespace(monsters={23:dict(id=23,name='probe',exp=50)},map_data={}),_yield_learner=YieldLearner())
  if fresh:a._training_context=dict(map='a',map_readable=True,map_at=100,mobs=[23],mobs_at=100,party_visible=2,party_readable=True,party_at=100)
  for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total','training_forecast_now'):
   setattr(a,name,types.MethodType(getattr(training_ui,name),a))
  with patch('time.time',return_value=100),patch('time.monotonic',return_value=100):
   before=a.training_gain_context()
   for t in (98,99,100):a._yield_learner.observe(before,dict(exp=9,kills=1),9,t)
   if before[0]:assert a.training_forecast_now()['gain']==9
   a.state['training_auto_context']=not initial
   forecast=a.training_forecast_now()
   assert a._yield_learner.estimate(a.training_gain_context(),100) is None
   if forecast['available']:assert forecast['gain']!=9
   a.state['training_auto_context']=initial;a.training_forecast_now()
   assert a._yield_learner.estimate(before,100) is None,'Old mode calibration revived'
   cases.append(dict(from_auto=initial,fresh_context=fresh,next_available=forecast['available']))
report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic mode-switch learned-yield scoping with identical target/party where possible,not livegameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

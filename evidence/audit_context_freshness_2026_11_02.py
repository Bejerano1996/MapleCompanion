from pathlib import Path
import sys,json,hashlib,types
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import training_ui
from training_yield import YieldLearner
checks=[]
for field in ('map_at','mobs_at','party_at'):
 for age in (19.999,20,20.001,21,45,100):
  a=types.SimpleNamespace(state=dict(training_auto_context=True,character_exp={'level':32,'exp':1000},character_exp_at=100,training_personal_gain=None),db=types.SimpleNamespace(monsters={23:dict(id=23,name='probe',exp=50)},map_data={'a':{'monsters':[{'id':'23'}]}}))
  a._training_context=dict(map='a',map_readable=True,map_at=100,mobs=[23],mobs_at=100,party_readable=True,party_visible=4,party_at=100)
  for name in ('training_target','training_plausible_targets','training_gain_context','training_forecast_now','training_party_total'):
   setattr(a,name,types.MethodType(getattr(training_ui,name),a))
  a._yield_learner=YieldLearner()
  with patch('time.time',return_value=100),patch('time.monotonic',return_value=100):
   key=a.training_gain_context()
   for t in (98,99,100):a._yield_learner.observe(key,dict(exp=9,kills=1,party_exp=2),9,t)
   assert a.training_forecast_now()['gain']==9
   a._training_context[field]=100-age
   f=a.training_forecast_now()
   if age>20:
    assert not f['available'],(field,age,f)
    assert a._yield_learner.progress(a.training_gain_context(),100)==0
   else:assert f['available'] and f['gain']==9,(field,age,f)
   a._training_context[field]=100
   if age>20:assert a._yield_learner.estimate(a.training_gain_context(),100) is None,'Old calibration revived'
   checks.append(dict(field=field,age=age,available=f['available']))
report=dict(ok=True,cases=checks,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Offline simulated freshness boundaries; no game capture or gameplay input')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=True,cases=len(checks),source_sha=report['source_sha'])))

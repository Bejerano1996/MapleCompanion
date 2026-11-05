from pathlib import Path
import sys,json,types,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import training_ui
from training_yield import YieldLearner
cases=0
variants=[('missing',{},True),('none',{'a':None},True),('no_index',{'a':{}},True),('empty',{'a':{'monsters':[]}},False),('contradictory',{'a':{'monsters':[{'id':24}]}},False),('malformed_list',{'a':{'monsters':[None]}},True),('missing_id',{'a':{'monsters':[{}]}},True),('numeric_string',{'a':{'monsters':[{'id':'23'}]}},True)]
for label,metadata,allowed in variants:
 for seed in range(50):
  now=100.+seed;app=types.SimpleNamespace(state=dict(training_auto_context=True,training_target='24',character_exp=dict(level=27,exp=1000),character_exp_at=now),db=types.SimpleNamespace(monsters={23:dict(id=23,name='Visible',exp=13),24:dict(id=24,name='Saved',exp=50)},map_data={'a':{'monsters':[{'id':23}]}}))
  app._training_context=dict(map='a',map_readable=True,map_at=now,mobs=[23],mobs_at=now,party_visible=2,party_readable=True,party_at=now)
  for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total','training_forecast_now','training_observe_yield'):setattr(app,name,types.MethodType(getattr(training_ui,name),app))
  with patch('time.time',return_value=now),patch('time.monotonic',return_value=now):
   key=app.training_gain_context();app._yield_learner=YieldLearner()
   for _ in range(3):app._yield_learner.observe(key,dict(exp=16,kills=1,party_exp=3),16,now)
   app.db.map_data=metadata;target=app.training_target();forecast=app.training_forecast_now()
   if allowed:assert target['id']==23 and forecast['available'],(label,target,forecast)
   else:
    assert target is None and not forecast['available'],(label,target,forecast)
    assert app._yield_learner.progress(app.training_gain_context(),now)==0
   assert target is None or target['id']!=24
   app.db.map_data={'a':{'monsters':[{'id':23}]}}
   if not allowed:
    assert app._yield_learner.estimate(app.training_gain_context(),now) is None
    for _ in range(3):assert app.training_observe_yield(dict(exp=16,kills=1,party_exp=3),dict(level=27,exp=1000),dict(level=27,exp=1016))
    assert app._yield_learner.estimate(app.training_gain_context(),now)==16
  cases+=1
report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Production target/forecast/learner across empty,contradictory,missing,malformed mapindices; savedmanualtarget never used in auto; missingmetadata staysunknown not proofspawn. Synthetic only')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

from pathlib import Path
import sys,json,types,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import training_ui
from training_accounting import TrainingAccountant
from training_yield import YieldLearner
from session_rewards import session_token
cases=0
for mode in ('unknown_map','mixed_species'):
 for seed in range(100):
  clock=[100.+seed];s=dict(id='audit',running_since=1,auto_rewards=True,exp=0,mesos=0,kills=0,party_exp=0);account=TrainingAccountant();token=session_token(s)
  app=types.SimpleNamespace(state=dict(training_auto_context=True,character_exp=dict(level=27,exp=1000)),db=types.SimpleNamespace(monsters={23:dict(id=23,name='A',exp=13),24:dict(id=24,name='B',exp=50)},map_data={'a':{'monsters':[{'id':'23'},{'id':'24'}]}}))
  app._training_context=dict(map='a',map_readable=True,mobs=[23],party_readable=True,party_visible=2)
  for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total','training_observe_yield','training_buffer_yield','training_forecast_now'):setattr(app,name,types.MethodType(getattr(training_ui,name),app))
  def poll(events,exp):
   clock[0]+=.2
   for field in ('map_at','mobs_at','party_at'):app._training_context[field]=clock[0]
   previous=account.character;reading=dict(level=27,exp=exp);account.feed(s,token,events,reading,clock[0])
   if account.character is reading:app.state['character_exp']=dict(reading);app.training_buffer_yield(account.last_delta,previous,reading)
   else:app.training_buffer_yield(account.last_delta)
  with patch('time.time',side_effect=lambda:clock[0]),patch('time.monotonic',side_effect=lambda:clock[0]):
   poll([],1000);poll([],1000);key=app.training_gain_context();app._yield_learner=YieldLearner()
   for _ in range(3):app._yield_learner.observe(key,dict(exp=16,kills=1,party_exp=3),16,clock[0])
   assert app._yield_learner.estimate(key,clock[0])==16
   if mode=='unknown_map':app._training_context['map_readable']=False
   else:app._training_context['mobs']=[23,24]
   events=[('exp',13),('bonus',3)];poll(events,1016)
   assert s['exp']==16 and app.training_target() is None
   assert not app.training_forecast_now()['available']
   assert app._yield_learner.estimate(app.training_gain_context(),clock[0]) is None
   app._training_context.update(map_readable=True,mobs=[23]);poll(events,1016)
   assert app._yield_learner.estimate(app.training_gain_context(),clock[0]) is None,'Old calibration revived'
   for i in range(3):events += [('exp',13),('bonus',3)];poll(events,1032+16*i)
   assert s['exp']==64 and s['party_exp']==12 and s['kills']==4
   assert app._yield_learner.estimate(app.training_gain_context(),clock[0])==16
  cases+=1
report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Production context selectors/accountant/yieldbuffer: unknownmap or mixedspecies preservesHUDtotals, clearsoldcalibration, threefreshknownsamplesrelearn; synthetic no liveOCR/game')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

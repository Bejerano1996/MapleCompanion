from pathlib import Path
import sys,types,json,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import training_context,training_ui
from training_yield import YieldLearner
cases=0
for oldparty in range(2,7):
 for newparty in range(2,7):
  if oldparty==newparty:continue
  for override in (False,True):
   clock=[100.];tracker=training_context.ContextTracker()
   a=types.SimpleNamespace(state=dict(training_auto_context=True,training_target='23',party=6,character_exp={'level':27,'exp':1000},character_exp_at=100.),db=types.SimpleNamespace(monsters={23:dict(id=23,name='A',exp=100)},map_data={'a':{'monsters':[{'id':23}]}}),_yield_learner=YieldLearner())
   for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total','training_forecast_now'):setattr(a,name,types.MethodType(getattr(training_ui,name),a))
   def feed(party):
    a._training_context=tracker.feed(dict(game=True,map='a',mobs=[23],party_visible=party),clock[0]);clock[0]+=1.
   with patch('time.time',side_effect=lambda:clock[0]),patch('time.monotonic',side_effect=lambda:clock[0]):
    feed(oldparty);feed(oldparty);old=a.training_gain_context()
    if override:a.state.update(training_personal_gain=14,training_gain_context=old)
    else:
     for i in range(3):a._yield_learner.observe(old,dict(exp=14,kills=1,party_exp=2),14,clock[0])
    assert a.training_forecast_now()['gain']==14
    feed(None);assert not a.training_forecast_now()['available']
    feed(newparty);assert not a.training_forecast_now()['available']
    feed(newparty);fresh=a.training_forecast_now()
    assert fresh['available'] and fresh['party']==newparty and fresh['source']=='visible mob / roster · estimated share'
    new=a.training_gain_context();assert new!=old
    assert a._yield_learner.estimate(new,clock[0]) is None
    for i in range(3):a._yield_learner.observe(new,dict(exp=17,kills=1,party_exp=3),17,clock[0])
    fresh=a.training_forecast_now();assert fresh['gain']==17 and fresh['source']=='observed EXP/event · inferred target'
   cases+=1
report=dict(ok=True,cases=cases,party_sizes=[2,6],old_gain_modes=['override','learned'],source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic roster hide/change/confirmation integrated with production context, learner and forecast; no actual party formula or kill verification/livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

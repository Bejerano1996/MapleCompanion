from pathlib import Path
import sys,json,types,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import training_ui
from training_yield import YieldLearner
cases=0
for count in range(2,7):
 for mode in ('hidden','expired'):
  for seed in range(30):
   now=100.+seed;app=types.SimpleNamespace(state=dict(training_auto_context=True,training_target='23',party=6,party_hits='me',training_party_levels=500,training_party_reference_level=27,training_personal_gain=999,training_gain_context=['23',6,'me',500,27],character_exp=dict(level=27,exp=1000),character_exp_at=now),db=types.SimpleNamespace(monsters={23:dict(id=23,name='Visible',exp=130)},map_data={'a':{'monsters':[{'id':23}]}}))
   app._training_context=dict(map='a',map_readable=True,map_at=now,mobs=[23],mobs_at=now,party_visible=count,party_readable=True,party_at=now)
   for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total','training_forecast_now','training_observe_yield'):setattr(app,name,types.MethodType(getattr(training_ui,name),app))
   with patch('time.time',return_value=now),patch('time.monotonic',return_value=now):
    forecast=app.training_forecast_now();assert forecast['party']==count and forecast['gain']!=999
    app._yield_learner=YieldLearner();key=app.training_gain_context()
    for _ in range(3):app._yield_learner.observe(key,dict(exp=16,kills=1,party_exp=3),16,now)
    assert app.training_forecast_now()['gain']==16
    if mode=='hidden':app._training_context['party_readable']=False
    else:app._training_context['party_at']=now-20.001
    assert not app.training_forecast_now()['available']
    assert app._yield_learner.estimate(app.training_gain_context(),now) is None
    for _ in range(3):assert app.training_observe_yield(dict(exp=16,kills=1,party_exp=3),dict(level=27,exp=1000),dict(level=27,exp=1016))
    forecast=app.training_forecast_now();assert forecast['available'] and forecast['gain']==16 and forecast['party'] is None
    restored=count%5+2;app._training_context.update(party_visible=restored,party_readable=True,party_at=now)
    forecast=app.training_forecast_now();assert forecast['party']==restored and forecast['gain']!=999
    assert app._yield_learner.estimate(app.training_gain_context(),now) is None
   cases+=1
report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Production automaticforecast with persistedmanualparty/hits/leveltotal/gain; hidden/expiredroster clearsoldyield, unknownsize canlearnpersonalEXPwithoutinventingsize, recoveredrosterresets; synthetic only')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

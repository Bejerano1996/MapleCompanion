from pathlib import Path
import sys,json,types,math,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import training_ui,leveling
cases=0;largest=0
with patch('time.time',return_value=100),patch('time.monotonic',return_value=100):
 for level in (1,2,5,30,50,89,90,99):
  for mobexp in (.1,1,2,13,1000000):
   for members in range(1,7):
    for current in (0,leveling.exp_to_next(level)-1):
     app=types.SimpleNamespace(state=dict(training_auto_context=True,party=1,party_hits='all',character_exp=dict(level=level,exp=current),character_exp_at=100),db=types.SimpleNamespace(monsters={23:dict(id=23,name='Probe',exp=mobexp)},map_data={'a':{'monsters':[{'id':23}]}}))
     app._training_context=dict(map='a',map_readable=True,map_at=100,mobs=[23],mobs_at=100,party_visible=members,party_readable=True,party_at=100)
     for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total','training_forecast_now'):setattr(app,name,types.MethodType(getattr(training_ui,name),app))
     clean=app.training_forecast_now();assert clean['available']
     for manual in (None,0,-1,True,'bad',float('nan')):
      app.state.update(party=6,party_hits='invalid',training_party_levels=manual,training_party_reference_level=1)
      f=app.training_forecast_now()
      assert f['available'] and f['party']==members
      assert f['gain']==clean['gain'] and f['kills']==clean['kills']
      assert math.isfinite(f['gain']) and f['gain']>0 and isinstance(f['kills'],int) and f['kills']>=1
      largest=max(largest,f['kills']);cases+=1
report=dict(ok=True,cases=cases,largest_estimated_kills=largest,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Automatic productionforecast boundarylevels1–99,mobEXP.1–1e6,visibleparty1–6,oneEXPleft/fulllevel; independencefrominvalidpersistedmanualweights/hits. Not serverformula/livegamevalidation')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

from pathlib import Path
import sys,json,random,hashlib,math,copy
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from companion_feature_model import utility_session_new,utility_session_toggle,utility_session_elapsed,utility_session_snapshot,utility_session_rates
cases=0
for seed in range(200):
 rng=random.Random(seed);now=0.;expected=0.;s=utility_session_new(now)
 for cycle in range(10):
  s=utility_session_toggle(s,now);active=rng.uniform(1,300);now+=active;expected+=active
  s.update(exp=s['exp']+rng.randint(1,200),mesos=s['mesos']+rng.randint(1,100),kills=s['kills']+1,cost=10)
  before=copy.deepcopy(s);saved=utility_session_snapshot(s,now)
  assert s==before,'Snapshot mutated running state'
  assert saved['running_since'] is None and math.isclose(saved['elapsed'],expected,rel_tol=1e-10)
  s=utility_session_toggle(s,now);paused=rng.uniform(1,5000);now+=paused
  rates=utility_session_rates(s,now)
  assert math.isclose(rates['seconds'],expected,rel_tol=1e-10)
  assert math.isclose(rates['exp_hour'],s['exp']*3600/expected,rel_tol=1e-10)
  assert math.isclose(rates['net_hour'],(s['mesos']-10)*3600/expected,rel_tol=1e-10)
  # Simulated reload starts paused and excludes all additional offline time.
  s=saved;now+=rng.uniform(1,5000)
  assert math.isclose(utility_session_elapsed(s,now),expected,rel_tol=1e-10)
  cases+=1
report=dict(ok=True,cycles=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic active/pause/save/reload timing and pickup-mode rates; no real saved-state writes or livegameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

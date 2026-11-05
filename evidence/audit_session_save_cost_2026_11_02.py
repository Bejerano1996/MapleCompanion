from pathlib import Path
import sys,json,tempfile,time,statistics,copy,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import app
from companion_feature_model import utility_session_new
session=utility_session_new();session.update(running_since=time.time(),elapsed=1000,exp=100000,mesos=50000,kills=500,observed_monsters={str(i):dict(name='fixture mob '+str(i),seen=50) for i in range(20)})
state=dict(utility_session=session,utility_session_history=[copy.deepcopy(dict(session,running_since=None)) for _ in range(50)],active=[str(i) for i in range(100)],done={str(i):[0,1] for i in range(100)},level=27,map='fixture')
a=app.App.__new__(app.App);a.state=state;a.set_status=lambda *args:None;a._saved='';durations=[]
with tempfile.TemporaryDirectory(prefix='save-cost-',dir=Path(__file__).resolve().parent) as folder:
 app.STATE_FILE=str(Path(folder)/'state.json')
 for _ in range(50):
  before=time.perf_counter();a.save_state();durations.append(time.perf_counter()-before)
  assert a.state['utility_session'] is session and session['running_since'] is not None
 saved=json.loads(Path(app.STATE_FILE).read_text());assert saved['utility_session']['running_since'] is None
 size=Path(app.STATE_FILE).stat().st_size
report=dict(ok=True,saves=50,synthetic_history=50,state_bytes=size,median_ms=round(statistics.median(durations)*1000,3),p95_ms=round(sorted(durations)[47]*1000,3),max_ms=round(max(durations)*1000,3),source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Actual save_state wrapper/atomic file writes on temporary synthetic state,no realstatewrites/UI/gameinteraction; filesystem cache affects timings')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

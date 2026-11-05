from pathlib import Path
import sys,json,tempfile,copy,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import app
session=dict(id='fixture',running_since=100,elapsed=10,exp=9,mesos=7,kills=1)
a=app.App.__new__(app.App);a.state=dict(utility_session=session);a._saved='previous';errors=[];a.set_status=lambda *args:errors.append(args)
with tempfile.TemporaryDirectory(prefix='save-failure-',dir=Path(__file__).resolve().parent) as folder:
 app.STATE_FILE=str(Path(folder)/'state.json')
 for index in range(50):
  session['exp']+=9;session['mesos']+=7;before=copy.deepcopy(session);saved_before=a._saved
  with patch('app.write_atomic',side_effect=OSError('synthetic locked file')):a.save_state()
  assert a.state['utility_session'] is session and session==before and a._saved==saved_before
  a.save_state();persisted=json.loads(Path(app.STATE_FILE).read_text())['utility_session']
  assert persisted['exp']==session['exp'] and persisted['mesos']==session['mesos']
  assert persisted['running_since'] is None and session['running_since']==100
 assert len(errors)==50
report=dict(ok=True,failure_recovery_cycles=50,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Actual save_state wrapper with mocked OSError then real temporary-file recovery; no real savedstate/UI/gameinteraction')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

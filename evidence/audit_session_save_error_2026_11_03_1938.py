from pathlib import Path
import sys,tempfile,json,hashlib,copy
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import app
cases=0
with tempfile.TemporaryDirectory(prefix='save-error-',dir=root.parent) as folder:
 statefile=Path(folder)/'state.json'
 with patch.object(app,'STATE_FILE',str(statefile)):
  for exp in (-1000,-1,0,1,500):
   for running in (False,True):
    for error in (PermissionError('Synthetic access denied'),OSError('Synthetic disk full')):
     statefile.write_text('{"previous":"valid"}',encoding='utf-8');disk=statefile.read_bytes()
     a=object.__new__(app.App);a._saved='previous-saved';statuses=[];a.set_status=lambda *args:statuses.append(args)
     current=dict(id=str(cases),elapsed=10.,running_since=900. if running else None,exp=exp,party_exp=17,kills=7,mesos=80,cost=90)
     a.state={'utility_session':current,'utility_session_history':[dict(current,running_since=None)]};before=copy.deepcopy(a.state)
     with patch('time.time',return_value=1000.),patch.object(app,'write_atomic',side_effect=error):a.save_state()
     assert a.state==before and a.state['utility_session'] is current
     assert a._saved=='previous-saved' and statefile.read_bytes()==disk
     assert len(statuses)==1 and statuses[0][1]=='red'
     with patch('time.time',return_value=1001.):a.save_state()
     persisted=json.loads(statefile.read_text())
     assert a.state==before and a.state['utility_session'] is current
     assert persisted['utility_session']['exp']==exp and persisted['utility_session']['party_exp']==17
     assert persisted['utility_session']['running_since'] is None
     assert persisted['utility_session']['elapsed']==(111. if running else 10.)
     assert persisted['utility_session_history']==before['utility_session_history']
     assert json.loads(a._saved)==persisted
     cases+=1
report=dict(ok=True,cases=cases,error_modes=['PermissionError','OSError'],retry_succeeded=True,in_memory_session_identity_preserved=True,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Actual CompanionApp.save_state wrapper+base, object without Tk; injected write errors then real atomic tempfile retry, no user state/game')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

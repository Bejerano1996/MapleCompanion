from pathlib import Path
import sys,types,json,copy,hashlib,tkinter as tk
from unittest.mock import patch
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
import companion_tools as tools
from companion_widgets import ui_walk_widgets
from session_reader import RewardRead
root=tk.Tk();root.withdraw();errors=[];root.report_callback_exception=lambda k,e,t:errors.append(str(e));cases=0
try:
 for prior in (45,-100):
  for seed in range(10):
   clock=[100.+seed];pending=[];session=dict(id='old',running_since=90,elapsed=5,auto_rewards=True,exp=prior,exp_is_net=True,kills=3,party_exp=9,mesos=40,cost=5,note='')
   app=types.SimpleNamespace(root=root,state=dict(utility_session=session,utility_session_history=[],training_auto_context=False,map='a'),db=types.SimpleNamespace(maps={'a':{'name':'A'}}),save_state=lambda:None,render_levelup=lambda:None,training_session_counter=lambda parent:None,training_forecast_text=lambda:'Synthetic forecast',context_summary=lambda:'A',training_gain_context=lambda:['mob',1,'all',None,27],training_buffer_yield=lambda *a:False)
   app.training_accept_character=lambda r:app.state.update(character_exp=dict(r));app.run_bg=lambda job,loaded,on_error:pending.append(loaded);app.utility_poll_rewards=lambda:None
   frame=tk.Frame(root,bg=tools.C['bg']);frame.pack()
   with patch.object(tools,'window_rect',return_value=(0,0,1,1)),patch('time.time',side_effect=lambda:clock[0]),patch('time.monotonic',side_effect=lambda:clock[0]):
    tools.utility_render_session(app,frame);root.update_idletasks();clock[0]+=.2;tools.utility_poll_rewards(app);late=pending.pop()
    next(w for w in ui_walk_widgets(frame) if isinstance(w,tk.Button) and w.cget('text')=='Finish & archive').invoke();root.update_idletasks()
    archived=copy.deepcopy(app.state['utility_session_history']);fresh=app.state['utility_session'];assert len(archived)==1 and archived[0]['exp']==prior and archived[0]['running_since'] is None
    assert fresh['id']!='old' and fresh['running_since'] is None and fresh['exp']==0
    late(dict(events=RewardRead([('exp',500),('bonus',100),('mesos',999)],False,[2]),character=dict(level=27,exp=2000)))
    assert app.state['utility_session_history']==archived and fresh['exp']==0 and fresh['mesos']==0
    next(w for w in ui_walk_widgets(frame) if isinstance(w,tk.Button) and w.cget('text')=='Start / resume').invoke();root.update_idletasks()
    def read(events,exp):
     clock[0]+=.2;tools.utility_poll_rewards(app);pending.pop()(dict(events=RewardRead(events,False),character=dict(level=27,exp=exp)))
    read([],1000);read([],1000);events=[('exp',13),('bonus',3),('mesos',17)];read(events,1016);read(events,1016)
    current=app.state['utility_session'];assert (current['exp'],current['party_exp'],current['kills'],current['mesos'])==(16,3,1,17)
    assert app.state['utility_session_history']==archived
   frame.destroy();cases+=1
 root.after(800,root.quit);root.mainloop();assert not errors,errors
 report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Actual SessionFinish&archive/Start buttons with pendingproductionread, positive/negativeoldEXP, immutablehistory/newsessionfreshbaseline; mocksaves/captures, no actualfile/game')
 Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
finally:root.destroy()


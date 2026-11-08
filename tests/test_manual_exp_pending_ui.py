from pathlib import Path
import sys,json,types,hashlib,tkinter as tk
from tkinter import ttk
from unittest.mock import patch
rootpath=Path(__file__).resolve().parents[1];sys.path.insert(0,str(rootpath))
import training_ui,companion_tools
from companion_widgets import ui_walk_widgets
from session_reader import RewardRead
root=tk.Tk();root.withdraw();errors=[];root.report_callback_exception=lambda k,e,t:errors.append(str(e));cases=0
try:
 for initial in (False,True):
  for seed in range(10):
   clock=[100.+seed];pending=[];session=dict(id='audit',running_since=1,auto_rewards=True,exp=0,kills=0,party_exp=0,mesos=0)
   app=types.SimpleNamespace(root=root,state=dict(utility_session=session,training_auto_context=initial,training_target='24',party=1,party_hits='all',character_exp=dict(level=27,exp=1000)),db=types.SimpleNamespace(monsters={23:dict(id=23,name='A',level=20,exp=13),24:dict(id=24,name='B',level=30,exp=50)},map_data={'a':{'monsters':[{'id':23},{'id':24}]}}),save_state=lambda:None,render_levelup=lambda:None)
   app._training_context=dict(map='a',map_readable=True,map_at=clock[0],mobs=[23],mobs_at=clock[0],party_visible=2,party_readable=True,party_at=clock[0])
   def dialog(title):w=tk.Toplevel(root);w.withdraw();return w
   app.ui_dialog=dialog;app.training_accept_character=lambda r:app.state.update(character_exp=dict(r));app.run_bg=lambda job,loaded,on_error:pending.append(loaded)
   for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total','training_buffer_yield','training_observe_yield'):setattr(app,name,types.MethodType(getattr(training_ui,name),app))
   app.utility_poll_rewards=lambda:companion_tools.utility_poll_rewards(app)
   def dispatch():clock[0]+=.2;app.utility_poll_rewards();return pending.pop()
   with patch.object(companion_tools,'window_rect',return_value=(0,0,1,1)),patch('time.time',side_effect=lambda:clock[0]),patch('time.monotonic',side_effect=lambda:clock[0]):
    for _ in range(2):dispatch()(dict(events=RewardRead([],False),character=dict(level=27,exp=1000)))
    old=dispatch();training_ui.training_setup(app);window=app._training_setup_window;root.update_idletasks()
    next(w for w in ui_walk_widgets(window) if isinstance(w,tk.Checkbutton)).invoke()
    entries=[w for w in ui_walk_widgets(window) if type(w) is tk.Entry]
    for entry,value in zip(entries,('27','2000','','')):entry.delete(0,'end');entry.insert(0,value)
    combos=[w for w in ui_walk_widgets(window) if isinstance(w,ttk.Combobox)]
    next(w for w in combos if len(w.cget('values'))==2).current(1)
    next(w for w in combos if tuple(w.cget('values'))==('1','2','3','4','5','6')).set('3')
    next(w for w in ui_walk_widgets(window) if isinstance(w,tk.Button) and w.cget('text')=='Apply').invoke();root.update_idletasks()
    assert app.state['training_auto_context'] is not initial
    events=[('exp',13),('bonus',3)];old(dict(events=RewardRead(events,False),character=dict(level=27,exp=1016)))
    assert app.state['character_exp']['exp']==2000,(initial,seed,app.state['character_exp'])
    assert session['exp']==0
    for _ in range(2):dispatch()(dict(events=RewardRead(events,False),character=dict(level=27,exp=2000)))
    for i in range(3):events += [('exp',11),('bonus',3)];dispatch()(dict(events=RewardRead(events,False),character=dict(level=27,exp=2014+14*i)))
    assert (session['exp'],session['party_exp'],session['kills'])==(42,9,3)
    assert app._yield_learner.estimate(app.training_gain_context(),clock[0])==14
   cases+=1
 assert not errors,errors
 report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='ActualSetup explicitEXP2000 with oldHUD1016pending: oldmustnotoverwriteusercalibration, freshbaseline+3new14windows count42; save mocked,noOCR/game')
 print(json.dumps(report))
finally:root.destroy()

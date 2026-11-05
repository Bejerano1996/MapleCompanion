from pathlib import Path
import sys,json,types,copy,gc,hashlib,tkinter as tk
from unittest.mock import patch
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
import training_ui,companion_tools
from companion_widgets import ui_walk_widgets
from session_reader import RewardRead
root=tk.Tk();root.withdraw();errors=[];root.report_callback_exception=lambda k,e,t:errors.append(str(e));pending=[];clock=[100.]
session=dict(id='audit',running_since=1,auto_rewards=True,exp=0,kills=0,mesos=0,party_exp=0)
app=types.SimpleNamespace(root=root,state=dict(utility_session=session,training_auto_context=False,training_target='23',party=1,party_hits='all',character_exp=dict(level=27,exp=1000)),db=types.SimpleNamespace(monsters={23:dict(id=23,name='A',level=20,exp=13)},map_data={}),save_state=lambda:None,render_levelup=lambda:None)
def dialog(title):w=tk.Toplevel(root);w.withdraw();return w
app.ui_dialog=dialog;app.training_accept_character=lambda r:app.state.update(character_exp=dict(r));app.run_bg=lambda job,loaded,on_error:pending.append(loaded)
for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total','training_buffer_yield','training_observe_yield'):setattr(app,name,types.MethodType(getattr(training_ui,name),app))
app.utility_poll_rewards=lambda:None # scheduledpolls are inert in this isolated UI test
try:
 with patch.object(companion_tools,'window_rect',return_value=(0,0,1,1)),patch('time.time',side_effect=lambda:clock[0]),patch('time.monotonic',side_effect=lambda:clock[0]):
  def dispatch():clock[0]+=.2;companion_tools.utility_poll_rewards(app);return pending.pop()
  for _ in range(2):dispatch()(dict(events=RewardRead([],False),character=dict(level=27,exp=1000)))
  events=[];total=0
  for cycle in range(40):
   cb=dispatch();before=copy.deepcopy(app.state);training_ui.training_setup(app);window=app._training_setup_window;root.update_idletasks()
   entries=[w for w in ui_walk_widgets(window) if type(w) is tk.Entry]
   for entry,value in zip(entries,('99','99999','','999')):entry.delete(0,'end');entry.insert(0,value)
   next(w for w in ui_walk_widgets(window) if isinstance(w,tk.Checkbutton)).invoke()
   window.destroy();root.update_idletasks();assert app.state==before
   events += [('exp',13+cycle),('bonus',3)];total+=16+cycle
   cb(dict(events=RewardRead(events,False),character=dict(level=27,exp=1000+total)))
   assert session['exp']==total and app.state['character_exp']['exp']==1000+total
  root.after(800,root.quit);root.mainloop();gc.collect();root.update_idletasks()
  jobs=len(root.tk.call('after','info'));assert jobs==0,jobs
  assert not pending and not app._reward_busy and not errors,(pending,errors)
 report=dict(ok=True,cancel_cycles=40,session_exp=total,pending_after_jobs=jobs,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Own withdrawnTk actualSetup edited+closed withoutApply while production readpending; validresultstillcounts, scheduledtestpollsinert, scrolljobsflush. Savesmocked,no realfile/OCR/game')
 Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
finally:root.destroy()

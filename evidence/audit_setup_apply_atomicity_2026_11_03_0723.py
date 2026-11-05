from pathlib import Path
import sys,types,json,copy,hashlib,tkinter as tk
from tkinter import ttk
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
import training_ui,leveling
from companion_widgets import ui_walk_widgets
root=tk.Tk();root.withdraw();errors=[];root.report_callback_exception=lambda k,e,t:errors.append(str(e));saves=[];accepted=[]
app=types.SimpleNamespace(state=dict(training_auto_context=True,party=1,party_hits='all',character_exp=dict(level=27,exp=1000),training_personal_gain=16),db=types.SimpleNamespace(monsters={23:dict(id=23,name='Probe',level=20,exp=13)},map_data={}),save_state=lambda:saves.append(True),render_levelup=lambda:None)
def dialog(title):
 w=tk.Toplevel(root);w.withdraw();return w
app.ui_dialog=dialog
for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total'):setattr(app,name,types.MethodType(getattr(training_ui,name),app))
def accept(r):accepted.append(r);app.state['character_exp']=dict(r)
app.training_accept_character=accept;training_ui.training_setup(app);window=app._training_setup_window;root.update_idletasks()
entries=[w for w in ui_walk_widgets(window) if type(w) is tk.Entry];assert len(entries)==4,[(type(w).__name__,w.get()) for w in entries]
party=next(w for w in ui_walk_widgets(window) if isinstance(w,ttk.Combobox) and tuple(w.cget('values'))==('1','2','3','4','5','6'));party.set('3')
automatic=next(w for w in ui_walk_widgets(window) if isinstance(w,tk.Checkbutton));root.setvar(automatic.cget('variable'),False)
apply=next(w for w in ui_walk_widgets(window) if isinstance(w,tk.Button) and w.cget('text')=='Apply');before=copy.deepcopy(app.state)
cases=[(0,'0'),(0,'100'),(0,'abc'),(1,'-1'),(1,str(leveling.exp_to_next(27))),(2,'0'),(2,'bad'),(3,'0'),(3,'-1'),(3,'nan'),(3,'inf')]
def set_entries(values):
 for entry,value in zip(entries,values):entry.delete(0,'end');entry.insert(0,value)
for index,value in cases:
 values=['27','1000','','16'];values[index]=value;set_entries(values);apply.invoke();root.update_idletasks()
 assert app.state==before and not saves and not accepted and window.winfo_exists(),(index,value,app.state)
set_entries(['27','1000','','16']);apply.invoke();root.update_idletasks()
assert len(saves)==len(accepted)==1 and not window.winfo_exists()
assert app.state['party']==3 and app.state['training_auto_context'] is False
assert not errors,errors
report=dict(ok=True,invalid_apply_cases=len(cases),valid_apply_cases=1,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Own withdrawn Tk actualtrainingSetup/Apply invalidinputs preservestate; onevalidApplychangesinmemoryonly,mocked save, no realfile/OCR/game')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));root.destroy()



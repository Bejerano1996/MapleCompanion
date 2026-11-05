from pathlib import Path
import sys,types,json,copy,hashlib,tkinter as tk
from tkinter import ttk
from unittest.mock import patch
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
import training_ui
from companion_widgets import ui_walk_widgets
root=tk.Tk();root.withdraw();errors=[];root.report_callback_exception=lambda k,e,t:errors.append(str(e));cases=0
try:
 with patch('time.time',return_value=100),patch('time.monotonic',return_value=100):
  for automatic in (False,True):
   for gain in ('','16','25.5'):
    saves=[];accepted=[];original=dict(level=27,exp=1000,percent=1.5,source='Recorded HUD')
    app=types.SimpleNamespace(state=dict(training_auto_context=automatic,training_target='23',party=1,party_hits='all',character_exp=copy.deepcopy(original),character_exp_at=100),db=types.SimpleNamespace(monsters={23:dict(id=23,name='A',level=20,exp=13),24:dict(id=24,name='B',level=30,exp=50)},map_data={'a':{'monsters':[{'id':23},{'id':24}]}}),save_state=lambda:saves.append(True),render_levelup=lambda:None,training_accept_character=lambda r:accepted.append(r))
    app._training_context=dict(map='a',map_readable=True,map_at=100,mobs=[23],mobs_at=100,party_visible=2,party_readable=True,party_at=100)
    def dialog(title):w=tk.Toplevel(root);w.withdraw();return w
    app.ui_dialog=dialog
    for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total','training_forecast_now'):setattr(app,name,types.MethodType(getattr(training_ui,name),app))
    training_ui.training_setup(app);window=app._training_setup_window;root.update_idletasks()
    entries=[w for w in ui_walk_widgets(window) if type(w) is tk.Entry]
    for entry,value in zip(entries,('28','','100',gain)):entry.delete(0,'end');entry.insert(0,value)
    combos=[w for w in ui_walk_widgets(window) if isinstance(w,ttk.Combobox)]
    next(w for w in combos if len(w.cget('values'))==2).current(1)
    next(w for w in combos if tuple(w.cget('values'))==('1','2','3','4','5','6')).set('3')
    next(w for w in ui_walk_widgets(window) if isinstance(w,tk.Button) and w.cget('text')=='Apply').invoke();root.update_idletasks()
    assert len(saves)==1 and not accepted and not window.winfo_exists()
    assert app.state['character_exp']==original and app.state['character_exp_at']==100
    assert app.state['training_target']=='24'
    assert app.training_target()['id']==(23 if automatic else 24)
    assert app.state['training_gain_context']==app.training_gain_context()
    forecast=app.training_forecast_now();assert forecast['available']
    if gain:assert forecast['gain']==float(gain)
    app.state['training_auto_context']=not automatic
    if gain:assert app.state['training_gain_context']!=app.training_gain_context()
    cases+=1
 assert not errors,errors
 report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Actual Setup/Apply on withdrawnTk, blankEXP keeps existingHUDlevel/EXP/time even editedlevelfield; manualtarget/autoobservedtarget distinct, optionalgain contextscoped. Save mocked only,no game')
 Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
finally:root.destroy()

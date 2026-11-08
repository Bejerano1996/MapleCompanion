from pathlib import Path
import sys,os,json,tempfile,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
import app
import companion_portraits
real_fetch=companion_portraits.fetch_portrait
companion_portraits.fetch_portrait=lambda db,kind,identity,name:real_fetch(db,kind,identity,name) if (kind,str(identity)) in (("mob","23"),("npc","226")) else None
from companion_widgets import ui_walk_widgets
app.App.run_bg=lambda *a,**k:None
app.App.sync_from_game=lambda *a,**k:None
app.App.prefetch=lambda *a,**k:None
class NoHotkey:
    def __init__(self,*a,**k):pass
    def start(self):pass
app.HotkeyThread=NoHotkey
checks=[]
def check(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)
def pump():
    for _ in range(4):root.update();time.sleep(.015)
def texts(w):return [c.cget('text') for c in ui_walk_widgets(w) if isinstance(c,(tk.Label,tk.Button))]
with tempfile.TemporaryDirectory(prefix='map-reward-',dir=Path(__file__).parent) as folder:
    app.STATE_FILE=os.path.join(folder,'state.json')
    Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'auto_on_v2':True,'active':['10113'],'expanded':'10113','level':27,'map':'010005000','done':{'10113':[0]}}),encoding='utf-8')
    root=tk.Tk();errors=[];root.report_callback_exception=lambda x,y,z:errors.append(str(y))
    a=app.App(root);a.db.load_indexes()



    from training_model import training_forecast
    from training_accounting import TrainingAccountant
    from session_rewards import session_token
    a.training_accept_character({'level':27,'exp':63600})
    a.state['training_target']='23';a.state['party']=1;a.render_levelup();pump()
    check('Counter rounds up to two Evil Eye',any('≈2 Evil Eye' in t for t in texts(a.lvl_strip)))
    a.state['party']=2;a.render_levelup();pump()
    check('Party share changes counter',any('≈3 Evil Eye' in t for t in texts(a.lvl_strip)))
    a.state['training_personal_gain']=9;a.render_levelup();pump()
    check('Personal gain includes bonus',a.training_forecast_now()['kills']==8)
    a.state.update(training_personal_gain=None,training_party_levels=54,training_party_reference_level=27)
    a.training_accept_character({'level':28,'exp':0})
    check('Party total follows own level-up',a.training_party_total()==55 and a.training_forecast_now()['gain']==29)
    a.state.update(training_party_levels=None,training_party_reference_level=None)
    a.ui_tools();pump()
    check('Session includes counter',any('EXP left' in t for t in texts(a._tools_window)))
    for scale in (1.0,1.15,1.3):
        a.set_text_size(scale);a.companion_exp_details();pump()
        setup=a._training_setup_window
        check('Setup has Apply at '+str(scale),'Apply' in texts(setup));setup.destroy();pump()
    session=a.state['utility_session'];session.update(running_since=100,exp=0,mesos=0,kills=0,cost=5)
    account=TrainingAccountant();token=session_token(session)
    account.feed(session,token,[],{'level':27,'exp':1000},0)
    account.feed(session,token,[('exp',7),('bonus',2),('mesos',10)],{'level':27,'exp':1009},5)
    account.feed(session,token,[('exp',7),('bonus',2),('mesos',10)],{'level':27,'exp':1009},6)
    check('Bar and log not doubled',session['exp']==9 and session['party_exp']==2 and session['mesos']==10)
    account.feed(session,token,[('exp',7),('bonus',2),('mesos',10)],{'level':27,'exp':900},10)
    check('Death reflected as net',session['exp']==-100)
    a._utility_show('session');pump()
    next(v for v in ui_walk_widgets(a._tools_window) if isinstance(v,tk.Button) and v.cget('text')=='Save totals').invoke();pump()
    check('Negative net EXP does not break Save',session['exp']==-100)
    now=time.time()
    a._training_context=dict(game=True,at=now,map=a.state['map'],map_at=now,map_readable=True,mobs=[23],mobs_at=now,party_visible=4,party_at=now,party_readable=True)
    a.state['training_auto_context']=True
    check('Automatic forecast uses visible roster',a.training_forecast_now()['party']==4)
    a._training_context['party_readable']=False
    check('Hidden roster does not assume solo or saved party',not a.training_forecast_now()['available'])
    a._training_context['party_readable']=True;a._training_context['mobs']=[23,24]
    check('Multiple visible mobs do not select arbitrary target',a.training_target() is None)
    a.state['training_auto_context']=False
    check('Manual target remains available',a.training_target()['id']==23)
    a.state['training_auto_context']=True;a._context_busy=False
    a.run_bg=lambda fn,callback,on_error=None:callback(dict(game=True,map=a.state['map'],party_visible=4,mobs=[23],captured_at=time.time()))
    a._context_last_poll=-100;a.context_poll()
    check('First automatic context read remains unconfirmed',a._training_context.get('party_visible') is None)
    a._context_last_poll=-100;a.context_poll()
    check('Confirmed automatic context reaches session UI',a._training_context['party_visible']==4 and '4 visible' in a.context_summary())
    check('No Tk callback errors',not errors)
    print(json.dumps({'ok':True,'checks':checks}));root.destroy()

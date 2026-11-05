"""Own-widget integration checks; no game capture, hotkeys or gameplay input."""
import os,sys,json,tempfile,time,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app,widgets,companion_market
from companion_feature_model import utility_session_new
import tkinter as tk
class NoHotkey:
    def __init__(self,*a,**k):pass
    def start(self):pass
app.HotkeyThread=NoHotkey
app.App.sync_from_game=lambda self,*a,**k:None
app.App.prefetch=lambda self:None
checks=[]
def require(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)
def descendants(w):
    for child in w.winfo_children():
        yield child
        yield from descendants(child)
def click(w,text):
    button=next(c for c in descendants(w) if isinstance(c,tk.Button) and c.cget('text')==text)
    button.invoke();return button
def pump(seconds=.1):
    until=time.monotonic()+seconds
    while time.monotonic()<until:root.update();time.sleep(.01)
with tempfile.TemporaryDirectory(prefix='integration-state-',dir=str(Path(__file__).resolve().parent)) as folder:
    app.STATE_FILE=os.path.join(folder,'state.json')
    fixture={'level':26,'character_class':'Thief','profile_name':'Integration fixture','auto_sync':False,'auto_on_v2':True,'active':['10306'],'tracked':['10306'],'progress':{'10306':{'0':40}},'done':{},'completed':[],'map':'010005061','tab':'quests','idle_alpha':1.0,'geometry':'470x640+12+720','pos':[12,720],'panel_size':[470,640],'compact_v3':True,'utility_session':utility_session_new()}
    Path(app.STATE_FILE).write_text(json.dumps(fixture),encoding='utf-8')
    root=tk.Tk();errors=[];root.report_callback_exception=lambda a,b,c:errors.append(str(b))
    a=app.App(root);a.db.load_indexes();pump(.3)
    require('Light palette installed',widgets.C['bg']=='#f4f3f8' and widgets.C['text']=='#252735')
    require('Original Umbrale profile and tracked data preserved',a.state['active']==fixture['active'] and a.state['progress']==fixture['progress'])
    require('Companion profile visible',a.profile_name.cget('text')=='Integration fixture')
    for key,title in app.TABS:
        a.set_tab(key);pump()
        require('Original tab retained: '+key,a.state['tab']==key and a.scroll.inner.winfo_children())
    a.ui_tools();pump()
    require('Tools window available',a._tools_window.winfo_exists())
    for key in ('session','route','timers','saved','compare','quick'):
        a._utility_show(key);pump()
        require('Companion utility renders: '+key,a._tools_window.winfo_exists())
    original_wheel=root.bind_all('<MouseWheel>')
    a._tools_window.destroy();pump()
    baseline=root.bind_all('<MouseWheel>').strip()
    for repeat in range(10):a.ui_tools();pump(.02);a._tools_window.destroy()
    require('Repeated tools clean up wheel callbacks',root.bind_all('<MouseWheel>').strip()==baseline)
    a.ui_settings();pump()
    profile=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and 'Character profile' in w.title())
    fields=[w for w in descendants(profile) if isinstance(w,tk.Entry)]
    fields[0].delete(0,'end');fields[0].insert(0,'Saved profile')
    click(profile,'Save changes');pump()
    require('Profile save persisted',json.loads(Path(app.STATE_FILE).read_text())['profile_name']=='Saved profile')
    a.global_query.set('Snail');a._companion_search_kind.set('Monsters');a.ui_search();pump()
    require('Global monster search maps to native API',a.mob_query.get()=='Snail' and a.state['tab']=='mobs')
    a.open_add_dialog();pump()
    add=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and 'Add a quest' in w.title())
    require('Quest picker opens without replacing journal',a.state['active']==fixture['active']);add.destroy()
    a.ui_watchlist();pump()
    watch=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and 'Farming watchlist' in w.title())
    entry=next(w for w in descendants(watch) if isinstance(w,tk.Entry));entry.insert(0,'Snail Shell');click(watch,'Save item');pump()
    require('Watchlist persists',a.state['companion_watchlist']==['Snail Shell']);watch.destroy()
    a.ui_mesowatch('Snail Shell');pump()
    meso=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and 'MesoWatch' in w.title())
    entries=[w for w in descendants(meso) if isinstance(w,tk.Entry)];entries[1].insert(0,'75');click(meso,'Save manual price note');pump()
    require('MesoWatch quote is explicitly manual and persisted',a.state['companion_price_notes']['Snail Shell']['price']==75 and 'manual' in a.state['companion_price_notes']['Snail Shell']['source']);meso.destroy()
    companion_market.market_fetch=lambda name=None: {'name':name,'listings':[]} if name else {'at':time.time(),'items':[{'name':'Snail Shell','typical':75,'range':[70,80],'sold':4}]}
    a.ui_market();pump(.6)
    require('Live market pane loads using same client interface',a._market_view_state['index']['items'][0]['typical']==75)
    require('MesoWatch accessible alongside automatic source',any(isinstance(w,tk.Button) and 'MesoWatch' in w.cget('text') for w in descendants(a._market_window)))
    a._market_window.destroy();pump(.1)
    a.companion_overview();pump()
    require('Native quest guide remains accessible',any(isinstance(w,tk.Toplevel) and 'Your next step' in w.title() for w in root.winfo_children()))
    a.save_state();saved=json.loads(Path(app.STATE_FILE).read_text())
    require('Quest data survives all new screens',saved['progress']==fixture['progress'] and saved['tracked']==fixture['tracked'])
    require('No Tk callback errors',not errors)
    if '--preview' in sys.argv:
        for child in root.winfo_children():
            if isinstance(child,tk.Toplevel):child.destroy()
        if '--large-preview' in sys.argv:a.set_text_size(1.3)
        a.set_tab('quests');root.title('UMBRΛLE · Companion integration preview');root.after(120000,root.destroy);root.mainloop()
    else:
        for job in root.tk.call('after','info'):root.tk.call('after','cancel',job)
        root.destroy()
report={'ok':True,'count':len(checks),'checks':checks,'errors':errors}
Path(__file__).with_name('integration-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)

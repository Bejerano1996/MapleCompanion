"""Compact training target and validated level-up forecast UI."""
import tkinter as tk
from tkinter import ttk
import time,math
import widgets
from widgets import C,FONT,label,font_size,ScrollArea
from companion_widgets import ui_button
from training_model import training_forecast,character_reading,absolute_exp,adjusted_party_total


def training_target(self):
    selected=str(self.state.get('training_target') or '')
    if selected:
        return next((m for m in self.db.monsters.values() if str(m['id'])==selected),None)
    mobs=(self.db.map_data.get(self.state.get('map')) or {}).get('monsters') or []
    for item in sorted(mobs,key=lambda m:-(m.get('count') or 0)):
        found=self.db.monsters.get(int(item['id']))
        if found and found.get('exp'):return found
    return None

def training_party_total(self):
    reading=self.state.get('character_exp') or {}
    return adjusted_party_total(self.state.get('training_party_levels'),self.state.get('training_party_reference_level'),reading.get('level'))

def training_gain_context(self):
    target=self.training_target();reading=self.state.get('character_exp') or {}
    return [str(target['id']) if target else '',self.state.get('party',1),self.state.get('party_hits','all'),self.training_party_total(),reading.get('level')]

def training_forecast_now(self):
    gain=self.state.get('training_personal_gain')
    context=self.state.get('training_gain_context')
    if context is not None and context!=self.training_gain_context():gain=None
    return training_forecast(self.state.get('character_exp'),self.training_target(),self.state.get('party',1),self.state.get('party_hits','all'),self.training_party_total(),time.time(),self.state.get('character_exp_at'),gain)

def training_accept_character(self,reading):
    absolute_exp(reading)
    import leveling
    reading=dict(reading);reading['need']=leveling.exp_to_next(reading['level']);reading.setdefault('percent',leveling.percent(reading['exp'],reading['level']))
    self.state['character_exp']=reading;self.state['character_exp_at']=time.time()
    self.state['exp_bar']=[reading['exp'],reading.get('percent',100*reading['exp']/reading['need'])]
    if self.state['level']!=reading['level']:
        self.level.set(str(reading['level']));self.set_level()
    self.render_levelup()

def training_on_exp_bar(self,texts,confirm):
    reading=character_reading(texts)
    if reading and confirm(('validated-character-level',),reading['level']):self.training_accept_character(reading)

def training_forecast_text(self):
    f=self.training_forecast_now()
    if not f['available']:return f['reason']
    mark='Last read · ' if f['stale'] else ''
    return f"{mark}≈{f['kills']:,} {f['mob']} → Lv {f['next_level']}\n{f['remaining']:,} EXP left · {f['gain']:g} EXP/kill · {f['source']}"

def training_render_levelup(self):
    f=self.training_forecast_now();r=self.state.get('character_exp')
    spec=('training-v3',tuple(sorted((r or {}).items())),tuple(sorted(f.items())),widgets.text_scale)
    if spec==self._lvl_spec:return
    self._lvl_spec=spec
    for child in self.lvl_strip.winfo_children():child.destroy()
    head=tk.Frame(self.lvl_strip,bg=C['card']);head.pack(fill='x',padx=6,pady=3)
    text=f"EXP {r.get('percent',0):.2f}%" if r else 'EXP —'
    label(head,text,bg='card',fg='muted',size=8).pack(side='left')
    ui_button(head,'Setup',self.companion_exp_details,compact=True,tip='Level, EXP, target & party').pack(side='right')
    text=self.training_forecast_text().split('\n')[0]
    label(self.lvl_strip,text,bg='card',fg='gold' if f['available'] else 'muted',size=8,anchor='w',justify='left',wraplength=max(200,self.panel_width()-35)).pack(fill='x',padx=6,pady=(0,4))
    if getattr(self,'_training_setup_refresh',None):self._training_setup_refresh()

def training_refresh_exp_pill(self):
    if not hasattr(self,'exp_pill'):return
    r=self.state.get('character_exp');f=self.training_forecast_now()
    text=f"{r.get('percent',0):.1f}%" if r else ''
    self.exp_pill.config(text=text)
    self.exp_pill.tip.text=self.training_forecast_text()

def training_setup(self):
    existing=getattr(self,'_training_setup_window',None)
    if existing and existing.winfo_exists():existing.lift();return
    w=self.ui_dialog('Training · level & party');self._training_setup_window=w;self._companion_exp_window=w;w.geometry('460x600');w.minsize(400,380)
    dialog=w;area=ScrollArea(dialog);area.pack(fill='both',expand=True);w=area.inner
    r=self.state.get('character_exp') or {}
    values={}
    def field(title,key,value):
        label(w,title,fg='muted',size=9).pack(anchor='w',padx=18,pady=(6,1))
        v=tk.StringVar(value=str(value));tk.Entry(w,textvariable=v,font=(FONT,font_size(10)),bg=C['card'],fg=C['text'],insertbackground=C['text']).pack(fill='x',padx=18,ipady=4);values[key]=v
    field('Level','level',r.get('level',self.state.get('level',1)))
    field('Current EXP · leave blank to keep automatic reading','exp',r.get('exp',''))
    label(w,'Target monster',fg='muted',size=9).pack(anchor='w',padx=18,pady=(8,1))
    monsters=sorted(self.db.monsters.values(),key=lambda m:m.get('display') or m['name'])
    names={f"{m.get('display') or m['name']} · Lv {m.get('level','?')}":m for m in monsters if m.get('exp')}
    target=self.training_target();target_name=next((name for name,m in names.items() if target and m['id']==target['id']),'')
    target_var=tk.StringVar(value=target_name)
    ttk.Combobox(w,textvariable=target_var,values=list(names),state='readonly',height=8).pack(fill='x',padx=18)
    party=tk.StringVar(value=str(self.state.get('party',1)));hits=tk.StringVar(value=self.state.get('party_hits','all'))
    line=tk.Frame(w,bg=C['bg']);line.pack(fill='x',padx=18,pady=8)
    label(line,'Party on map',fg='muted',size=9).pack(side='left')
    ttk.Combobox(line,textvariable=party,values=['1','2','3','4','5','6'],state='readonly',width=3).pack(side='left',padx=6)
    hit_box=ttk.Combobox(line,textvariable=hits,values=['all','me','leech'],state='readonly',width=7);hit_box.pack(side='left')
    widgets.Tooltip(hit_box,'all: equal damage · me: only you hit · leech: others hit. Only eligible members on this map count.')
    field('Party level total · blank assumes equal levels','levels',self.training_party_total() or '')
    saved_gain=self.state.get('training_personal_gain') if self.state.get('training_gain_context') in (None,self.training_gain_context()) else None
    field('Your total EXP per kill · optional override incl. bonus','gain',saved_gain or '')
    feedback=label(w,'',fg='red',size=9,wraplength=410,justify='left');feedback.pack(fill='x',padx=18,pady=5)
    def save():
        try:
            lv=int(values['level'].get());n=int(values['exp'].get()) if values['exp'].get().strip() else None
            levels=int(values['levels'].get()) if values['levels'].get().strip() else None
            gain=float(values['gain'].get()) if values['gain'].get().strip() else None
            if not 1<=lv<=99:raise ValueError('Level must be 1–99 for this EXP table')
            if levels is not None and levels<lv+int(party.get())-1:raise ValueError('Check party level total')
            if gain is not None and (not math.isfinite(gain) or gain<1):raise ValueError('EXP per kill must be at least 1')
            if n is not None:absolute_exp({'level':lv,'exp':n})
        except (ValueError,TypeError) as error:feedback.config(text=str(error));return
        self.state.update(party=int(party.get()),party_hits=hits.get(),training_party_levels=levels,training_party_reference_level=lv if levels is not None else None,training_personal_gain=gain)
        if target_var.get() in names:self.state['training_target']=str(names[target_var.get()]['id'])
        if n is not None:
            import leveling
            self.training_accept_character({'level':lv,'exp':n,'percent':leveling.percent(n,lv),'need':leveling.exp_to_next(lv),'source':'Manual calibration'})
        self.state['training_gain_context']=self.training_gain_context()
        self.save_state();self._lvl_spec=None;self.render_levelup();dialog.destroy()
    ui_button(w,'Apply',save,primary=True).pack(fill='x',padx=18,pady=5)
    label(w,'Formula estimates your share; actual party EXP is included in bar totals.',fg='muted',size=8,wraplength=410,justify='left').pack(fill='x',padx=18,pady=4)
    def closed(event):
        if event.widget==w:self._training_setup_refresh=None
    w.bind('<Destroy>',closed,add='+');area.commit()

def training_session_counter(self,parent):
    row=tk.Frame(parent,bg=C['card']);row.pack(fill='x',padx=12,pady=(4,8))
    text=label(row,'',bg='card',fg='gold',size=9,justify='left',anchor='w',wraplength=350);text.pack(fill='x')
    ui_button(row,'Target / party / EXP',self.companion_exp_details,compact=True).pack(anchor='w',pady=4)
    self._training_session_forecast_label=text

def install_training_ui(cls):
    for name,fn in list(globals().items()):
        if name.startswith('training_') and callable(fn):setattr(cls,name,fn)
    cls.companion_exp_details=training_setup;cls.render_levelup=training_render_levelup;cls.refresh_exp_pill=training_refresh_exp_pill;cls.on_exp_bar=training_on_exp_bar

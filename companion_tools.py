from widgets import font_size
"""Companion utility screens adapted to Umbrale's public App APIs."""
import tkinter as tk
import time
from widgets import C,FONT,label,ScrollArea
from companion_widgets import ui_button,ui_card
from companion_feature_model import *
from companion_planner_model import *
from session_rewards import RewardTracker,session_token,apply_rewards
from session_reader import capture_rewards
from game_sync import window_rect

def ui_tools_indicator(self):
    due=sum(1 for timer in self.state.get('utility_timers',[]) if utility_timer_status(timer)[1])
    if hasattr(self,'tools_btn'):
        self.tools_btn.config(fg=C['gold'] if due else C['text'])
        tip=getattr(self.tools_btn,'_companion_tooltip',None)
        if tip:tip.text='Companion tools · Ctrl+K'+(f' · {due} reminders due' if due else '')

def utility_tick(self):
    if self.state['utility_session'].get('running_since') is not None:
        utility_track_current_map(self)
    self.utility_poll_rewards()
    due = []
    for timer in self.state.get('utility_timers', []):
        if not timer.get('fired') and utility_timer_status(timer)[1]:
            timer['fired'] = True
            due.append(timer['label'])
    if due:
        self.state['utility_notice'] = 'Reminder: ' + ', '.join(due)
        self.status.config(text=self.state['utility_notice'], fg=C['gold'])
        self.save_state()
    ui_tools_indicator(self)
    if getattr(self, '_utility_refresh', None):
        try:
            self._utility_refresh()
        except tk.TclError:
            self._utility_refresh = None
    self._utility_checkpoint = getattr(self, '_utility_checkpoint', 0) + 1
    if self._utility_checkpoint >= 30:
        self._utility_checkpoint = 0
        if self.state['utility_session'].get('running_since') is not None:
            self.save_state()
    self._utility_tick_job = self.root.after(1000, self.utility_tick)


def utility_poll_rewards(self):
    session=self.state['utility_session'];token=session_token(session)
    if session.get('running_since') is None or not session.get('auto_rewards',True):
        self._reward_token=None;return
    if getattr(self,'_reward_token',None)!=token:
        self._reward_tracker=RewardTracker();self._reward_token=token
    if getattr(self,'_reward_busy',False):return
    windows=[self.root]+[w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel)]
    hide=[window_rect(w) for w in windows if w.winfo_viewable()]
    tracker=self._reward_tracker;self._reward_busy=True
    def loaded(events):
        self._reward_busy=False
        current=self.state['utility_session']
        if session_token(current)!=token or getattr(self,'_reward_token',None)!=token:return
        delta=tracker.feed(events)
        self._reward_status='Game not found' if events is None else 'Reading reward log' if events else 'Waiting for visible rewards'
        if apply_rewards(current,token,delta):self.save_state()
        if getattr(self,'_utility_refresh',None):self._utility_refresh()
    def failed(error):
        self._reward_busy=False;self._reward_status='Reader unavailable · '+str(error)[:90]
    self.run_bg(lambda:capture_rewards(hide),loaded,on_error=failed)

def utility_open(self):
    previous = getattr(self, '_tools_window', None)
    if previous and previous.winfo_exists():
        previous.lift()
        return
    w = self.ui_dialog('Companion tools')
    self._tools_window = w
    w.geometry('480x640')
    w.minsize(440, 540)
    w.resizable(True, True)
    ui_button(w, 'Market prices', self.ui_market, primary=True, compact=True).pack(fill='x', padx=18, pady=(0, 8))
    tabs = tk.Frame(w, bg=C['bg'])
    tabs.pack(fill='x', padx=14, pady=(0, 6))
    area = ScrollArea(w)
    area.pack(fill='both', expand=True)
    def show(key):
        self._utility_refresh = None
        area.clear(False)
        for name, button in buttons.items():
            button.config(bg=C['button'] if key == name else C['card'])
        getattr(self, 'utility_render_' + key)(area.inner)
        area.commit()
    self._utility_show = show
    buttons = {}
    for index, (key, title) in enumerate([('session', 'Session'), ('route', 'Quest route'), ('timers', 'Reminders'), ('saved', 'Saved'), ('compare', 'Compare'), ('quick', 'Shortcuts')]):
        buttons[key] = ui_button(tabs, title, lambda k=key: show(k), compact=True)
        buttons[key].config(padx=6, font=(FONT, font_size(8)))
        buttons[key].grid(row=index // 3, column=index % 3, sticky='ew', padx=2, pady=2)
    for column in range(3):
        tabs.columnconfigure(column, weight=1, uniform='tools')
    def closed(event):
        if event.widget == w:
            self._utility_refresh = None
            self._utility_show = None
    w.bind('<Destroy>', closed, add='+')
    show('session')

def utility_entry(parent, title, value='', width=None):
    label(parent, title, fg='muted', bg='card', size=8).pack(anchor='w', padx=12, pady=(8, 2))
    var = tk.StringVar(value=str(value))
    entry = tk.Entry(parent, textvariable=var, bg=C['header_dark'], fg=C['text'],
                     insertbackground=C['text'], relief='flat', font=(FONT, font_size(10)), width=width)
    entry.pack(fill='x', padx=12, pady=(0, 5), ipady=5)
    entry.bind('<Control-a>', lambda e: (entry.selection_range(0, 'end'), 'break')[-1])
    return var

def utility_track_current_map(self):
    current=str(self.state.get('map') or '')
    readable=getattr(self,'_live_last_result',{}) or {}
    known=current in self.db.maps
    if self.state.get('auto_sync') and readable.get('_minimap_readable') is False:known=False
    record=self.db.maps.get(current,{})
    self.state['utility_session']=utility_session_track_map(self.state['utility_session'],
       current if known else None,record.get('displayName') or record.get('name') or current)

def utility_render_session(self, parent):
    s = self.state['utility_session']
    card = ui_card(parent)
    label(card, 'YOUR TRAINING SESSION', fg='gold', bg='card', size=9, bold=True).pack(anchor='w', padx=12, pady=(12, 4))
    elapsed = label(card, '', bg='card', size=24, bold=True)
    elapsed.pack(anchor='w', padx=12)
    metrics = label(card, '', fg='muted', bg='card', size=10, justify='left', anchor='w')
    metrics.pack(fill='x', padx=12, pady=5)
    map_label=label(card,'',fg='muted',bg='card',size=9,wraplength=390,justify='left')
    map_label.pack(fill='x',padx=12,pady=(0,4))
    controls = tk.Frame(card, bg=C['card'])
    controls.pack(fill='x', padx=12, pady=8)
    def toggle():
        utility_track_current_map(self)
        self.state['utility_session'] = utility_session_toggle(self.state['utility_session'])
        self.save_state()
        refresh()
    start = ui_button(controls, 'Start', toggle, primary=True, compact=True)
    start.pack(side='left')
    def finish():
        if self.state['utility_session'].get('running_since') is not None:utility_track_current_map(self)
        if not apply():
            return
        current = self.state['utility_session']
        snapshot = utility_session_snapshot(current)
        snapshot['finished_at'] = time.time()
        self.state['utility_session_history'] = [snapshot] + self.state['utility_session_history'][:49]
        self.state['utility_session'] = utility_session_new()
        self.save_state()
        for key, var in fields.items():
            var.set('0')
        note.set('')
        feedback.config(text='Session archived. Ready for a new session.', fg=C['green'])
        refresh()
        render_history()
    ui_button(controls, 'Finish & archive', finish, compact=True).pack(side='right')
    message = label(parent, 'Auto: visible EXP and mesos messages. Kills ≈ EXP events (including party). Costs are entered manually.', fg='muted', size=9, wraplength=400, justify='left')
    message.pack(fill='x', padx=20, pady=4)
    auto=tk.BooleanVar(value=s.get('auto_rewards',True))
    def auto_changed():
        self.state['utility_session']['auto_rewards']=auto.get();self._reward_token=None;self.save_state();refresh()
    tk.Checkbutton(parent,text='Auto read game',variable=auto,command=auto_changed,bg=C['bg'],fg=C['text'],selectcolor=C['card']).pack(anchor='w',padx=20)
    form = ui_card(parent)
    fields = {key: utility_entry(form, title, s.get(key, 0)) for key, title in
              [('kills', 'KILLS ≈'), ('exp', 'EXP GAINED'), ('mesos', 'MESOS GAINED'), ('cost', 'POTIONS / OTHER COSTS')]}
    note = utility_entry(form, 'SESSION NOTE', s.get('note', ''))
    feedback = label(form, '', fg='red', bg='card', size=9, wraplength=390)
    feedback.pack(fill='x', padx=12)
    def apply():
        try:
            values = {key: int(utility_number(var.get())) for key, var in fields.items()}
        except ValueError as exc:
            feedback.config(text=str(exc), fg=C['red'])
            return False
        if self.state['utility_session'].get('auto_rewards',True):
            values={key:value for key,value in values.items() if key=='cost'}
        self.state['utility_session'].update(values, note=note.get().strip()[:1000])
        self.save_state()
        feedback.config(text='Totals saved', fg=C['green'])
        refresh()
        return True
    ui_button(form, 'Save totals', apply, primary=True, compact=True).pack(fill='x', padx=12, pady=10)
    def refresh():
        current = self.state['utility_session']
        rates = utility_session_rates(current)
        elapsed.config(text=utility_format_time(rates['seconds']))
        start.config(text='Pause' if current.get('running_since') is not None else 'Start / resume')
        metrics.config(text=f"{current.get('exp',0):,} EXP · ≈{current.get('kills',0):,} kills · {current.get('mesos',0):,} mesos\n{rates['exp_hour']:,.0f} EXP/h · {rates['net_hour']:,.0f} net mesos/h")
        automatic=current.get('auto_rewards',True)
        auto.set(automatic)
        for key in ('kills','exp','mesos'):
            if automatic:fields[key].set(str(current.get(key,0)))
            for widget in form.winfo_children():
                if isinstance(widget,tk.Entry) and str(widget.cget('textvariable'))==str(fields[key]):widget.config(state='readonly' if automatic else 'normal',readonlybackground=C['header_dark'])
        if automatic:message.config(text=(getattr(self,'_reward_status','Start to read the reward log') if current.get('running_since') is not None else 'Paused · press Start / resume')+' · Kills ≈ EXP events, including party. Keep the reward log visible.')
        else:message.config(text='Manual mode · enter totals and save.')
        if current.get('map_unattributed'):
            map_text='Map data incomplete · excluded from map comparison'
        elif current.get('map_mixed'):
            map_text='Multiple maps · excluded from map comparison'
        elif current.get('map_id'):
            map_text='Session map: '+str(current.get('map_name') or current['map_id'])
        else:map_text='The session map is recorded when you start.'
        map_label.config(text=map_text)
    self._utility_refresh = refresh
    refresh()
    history_area = tk.Frame(parent, bg=C['bg'])
    history_area.pack(fill='x')
    def render_history():
        for child in history_area.winfo_children():
            child.destroy()
        history = self.state.get('utility_session_history', [])
        if not history:
            return
        f = ui_card(history_area)
        label(f, 'RECENT SESSIONS', fg='gold', bg='card', size=9, bold=True).pack(anchor='w', padx=12, pady=10)
        for old in history[:10]:
            rates = utility_session_rates(old)
            text = f"{old.get('map_name') or 'Map not recorded'} · {utility_format_time(rates['seconds'])} · {'≈' if old.get('kills_estimated') else ''}{old.get('kills', 0):,} kills · {rates['net_mesos']:,.0f} net mesos"
            label(f, text, bg='card', size=9, wraplength=390, justify='left').pack(anchor='w', padx=12, pady=4)
            if old.get('note'):
                label(f, old['note'], bg='card', fg='muted', size=8, wraplength=390, justify='left').pack(anchor='w', padx=12, pady=(0, 5))
    render_history()

def utility_render_compare(self,parent):
    label(parent,'COMPARE TRAINING MAPS',fg='gold',size=11,bold=True).pack(anchor='w',padx=20,pady=8)
    text='Rates use recorded totals and training time. Automatic kill counts are estimates from EXP messages. Sessions with detected map changes or missing map data are omitted. At least one recorded minute per map is required.'
    if getattr(self,'_comparison_demo',False):text='DEMO DATA · '+text
    label(parent,text,fg='muted',size=9,wraplength=390,justify='left').pack(fill='x',padx=20,pady=(0,8))
    controls=tk.Frame(parent,bg=C['bg']);controls.pack(fill='x',padx=16)
    results=tk.Frame(parent,bg=C['bg']);results.pack(fill='x')
    buttons={}
    def refresh(metric=None):
        if metric:self._comparison_metric=metric
        metric=getattr(self,'_comparison_metric','exp_hour')
        report=utility_compare_maps(self.state.get('utility_session_history',[]),metric)
        self._utility_last_comparison=report
        for child in results.winfo_children():child.destroy()
        for key,button in buttons.items():button.config(bg=C['button'] if key==metric else C['card'])
        if not report['maps']:
            label(results,'Archive a session of at least one minute on a known single map to build your comparison.',fg='muted',size=10,wraplength=390,justify='left').pack(fill='x',padx=20,pady=18)
        for index,row in enumerate(report['maps'],1):
            card=ui_card(results,pady=5)
            label(card,f"{index}. {row['map_name']}",bg='card',size=11,bold=True,wraplength=375,justify='left').pack(anchor='w',padx=12,pady=(12,4))
            label(card,f"{row['sessions']} sessions · {utility_format_time(row['seconds'])} recorded",bg='card',fg='muted',size=9).pack(anchor='w',padx=12,pady=2)
            label(card,f"{row['exp_hour']:,.0f} EXP/h · {row['kills_hour']:,.0f} kills/h",bg='card',size=11).pack(anchor='w',padx=12,pady=(4,2))
            label(card,f"{row['net_hour']:,.0f} net mesos/h",bg='card',fg='green' if row['net_hour']>=0 else 'red',size=10).pack(anchor='w',padx=12,pady=(0,8))
            if row['map_id'] in self.db.maps:
                ui_button(card,'Open GPS →',lambda r=row:self.start_route('comparison:'+r['map_id'],r['map_id']),compact=True).pack(anchor='w',padx=12,pady=(0,10))
        omitted=sum(report['excluded'].values())
        label(results,f"Excluded records: {omitted} · Maps below one minute: {report['below_minimum_maps']}",fg='muted',size=8,wraplength=390).pack(fill='x',padx=20,pady=10)
    for metric,title in [('exp_hour','EXP/h'),('net_hour','Net mesos/h'),('kills_hour','Kills/h')]:
        buttons[metric]=ui_button(controls,title,lambda m=metric:refresh(m),compact=True)
        buttons[metric].pack(side='left',padx=2)
    ui_button(controls,'Refresh',refresh,compact=True).pack(side='right')
    refresh()

def utility_render_timers(self, parent):
    label(parent, 'Local reminders for breaks, buffs or anything you choose.', fg='muted', size=9, wraplength=400, justify='left').pack(fill='x', padx=20, pady=5)
    form = ui_card(parent)
    title = utility_entry(form, 'REMINDER', 'Take a break')
    minutes = utility_entry(form, 'MINUTES', '30')
    error = label(form, '', fg='red', bg='card', size=9)
    error.pack(fill='x', padx=12)
    rows = tk.Frame(parent, bg=C['bg'])
    rows.pack(fill='x')
    timer_labels = {}
    def redraw():
        timer_labels.clear()
        for child in rows.winfo_children():
            child.destroy()
        for timer in self.state['utility_timers']:
            f = ui_card(rows, pady=4)
            remaining, due = utility_timer_status(timer)
            label(f, timer['label'], bg='card', size=10, bold=True, wraplength=350).pack(anchor='w', padx=12, pady=(8, 2))
            countdown = label(f, 'Due · Reminder ready' if due else utility_format_time(remaining), bg='card', fg='gold' if due else 'muted', size=11)
            countdown.pack(anchor='w', padx=12, pady=(0, 8))
            timer_labels[timer['id']] = countdown
            controls = tk.Frame(f, bg=C['card'])
            controls.pack(fill='x', padx=12, pady=(0, 8))
            def restart(t=timer):
                t.update(due=time.time() + t['duration'], fired=False)
                self.save_state()
                redraw()
            def dismiss(t=timer):
                self.state['utility_timers'] = [item for item in self.state['utility_timers'] if item['id'] != t['id']]
                self.save_state()
                redraw()
            ui_button(controls, 'Restart', restart, compact=True).pack(side='left')
            ui_button(controls, 'Dismiss', dismiss, compact=True).pack(side='right')
    def add():
        try:
            if len(self.state['utility_timers']) >= 20:
                raise ValueError('You can keep up to 20 reminders')
            timer = utility_timer_new(title.get(), minutes.get())
        except ValueError as exc:
            error.config(text=str(exc))
            return
        self.state['utility_timers'].append(timer)
        self.save_state()
        error.config(text='')
        redraw()
    ui_button(form, 'Add reminder', add, primary=True, compact=True).pack(fill='x', padx=12, pady=10)
    def tick_labels():
        for timer in self.state['utility_timers']:
            countdown = timer_labels.get(timer['id'])
            if countdown and countdown.winfo_exists():
                remaining, due = utility_timer_status(timer)
                countdown.config(text='Due · Reminder ready' if due else utility_format_time(remaining), fg=C['gold'] if due else C['muted'])
    self._utility_refresh = tick_labels
    redraw()

def utility_render_saved(self, parent):
    label(parent, 'Saved maps & recent searches', size=12, bold=True).pack(anchor='w', padx=20, pady=8)
    current = str(self.state.get('map') or '')
    record = self.db.maps.get(current, {})
    form = ui_card(parent)
    name = utility_entry(form, 'MAP TITLE', record.get('displayName') or record.get('name') or current)
    note = utility_entry(form, 'NOTE', '')
    feedback = label(form, '', bg='card', fg='muted', size=9)
    feedback.pack(fill='x', padx=12)
    def bookmark():
        try:
            if current not in self.db.maps:
                raise ValueError('Choose a known current map first')
            self.state['map_bookmarks'] = utility_bookmark(self.state, current, name.get(), note.get())
            self.save_state()
            feedback.config(text='Current map saved')
            render_saved()
        except ValueError as exc:
            feedback.config(text=str(exc))
    ui_button(form, 'Save current map', bookmark, compact=True).pack(fill='x', padx=12, pady=10)
    saved_area = tk.Frame(parent, bg=C['bg'])
    saved_area.pack(fill='x')
    def render_saved():
        for child in saved_area.winfo_children():
            child.destroy()
        for entry in self.state.get('map_bookmarks', []):
            f = ui_card(saved_area, pady=4)
            label(f, entry.get('title') or entry['map_id'], bg='card', bold=True, size=10, wraplength=370).pack(anchor='w', padx=12, pady=8)
            if entry.get('note'):
                label(f, entry['note'], bg='card', fg='muted', size=9, wraplength=370, justify='left').pack(anchor='w', padx=12, pady=4)
            ui_button(f, 'GPS →', lambda e=entry: self.start_route('bookmark:' + e['map_id'], e['map_id']), compact=True).pack(anchor='w', padx=12, pady=(0, 8))
    render_saved()
    for query in self.state.get('search_history', [])[:10]:
        def search(q=query):
            self.global_query.set(q)
            self.ui_search()
        button = ui_button(parent, query, search, compact=True)
        button.config(wraplength=370, anchor='w', justify='left')
        button.pack(fill='x', padx=18, pady=3)

def utility_render_route(self, parent):
    current = str(self.state.get('map') or '')
    record = self.db.maps.get(current, {})
    header = ui_card(parent)
    label(header, 'QUEST ROUTE', fg='gold', bg='card', size=9, bold=True).pack(anchor='w', padx=12, pady=(12, 4))
    source_label = label(header, 'From ' + (record.get('displayName') or current or 'Unknown location'), bg='card', size=11, bold=True, wraplength=390)
    source_label.pack(anchor='w', padx=12, pady=4)
    label(header, 'Groups your remaining objectives into suggested stops using known portal connections. Collection drops are not guaranteed.', bg='card', fg='muted', size=9, wraplength=390, justify='left').pack(fill='x', padx=12, pady=5)
    results = tk.Frame(parent, bg=C['bg'])
    def refresh():
        current = str(self.state.get('map') or '')
        current_record = self.db.maps.get(current, {})
        source_label.config(text='From ' + (current_record.get('displayName') or current or 'Unknown location'))
        for widget in results.winfo_children():
            widget.destroy()
        objectives = planner_objectives(self.state, self.db.quests, self.guides)
        plan = planner_itinerary(str(self.state.get('map') or ''), self.db.map_data, objectives)
        self._utility_last_plan = plan
        if not objectives:
            label(results, 'No remaining objectives. Open the quest journal to add a quest or check the turn-in NPC.', fg='muted', size=10, wraplength=390, justify='left').pack(fill='x', padx=20, pady=14)
        elif not current:
            label(results, 'Choose your current map or sync the minimap first.', fg='muted', size=10, wraplength=390).pack(fill='x', padx=20, pady=14)
        else:
            label(results, f"Suggested stops: {len(plan['stops'])} · Portal steps: {plan['portals']}", size=10, bold=True).pack(anchor='w', padx=20, pady=10)
        for index, stop in enumerate(plan['stops'], 1):
            card = ui_card(results, pady=5)
            place = self.db.maps.get(stop['map'], {})
            title = place.get('displayName') or stop['map']
            label(card, f'{index}. {title}', bg='card', size=11, bold=True, wraplength=380).pack(anchor='w', padx=12, pady=(12, 3))
            label(card, 'Already here' if not stop['portals'] else f"Portal steps from previous stop: {stop['portals']}", fg='gold', bg='card', size=8).pack(anchor='w', padx=12, pady=3)
            for objective in stop['objectives']:
                text = f"{objective['name']} · {objective['remaining']} left\n{objective['quest']}"
                label(card, text, bg='card', fg='muted', size=9, wraplength=380, justify='left').pack(fill='x', padx=12, pady=5)
            ui_button(card, 'Open GPS →', lambda s=stop: self.start_route('planner:' + s['map'], s['map']), primary=True, compact=True).pack(anchor='w', padx=12, pady=(4, 12))
        for objective in plan['unplanned']:
            card = ui_card(results, pady=4)
            label(card, objective['name'], bg='card', size=10, bold=True, wraplength=380).pack(anchor='w', padx=12, pady=(10, 4))
            label(card, objective['reason'] + ' · Open the journal for available sources.', bg='card', fg='muted', size=9, wraplength=380, justify='left').pack(fill='x', padx=12, pady=4)
            ui_button(card, 'Open quest', lambda q=objective['qid']: self.ui_open_journal(q), compact=True).pack(anchor='w', padx=12, pady=(0, 10))
    ui_button(header, 'Refresh route', refresh, compact=True).pack(fill='x', padx=12, pady=10)
    results.pack(fill='x')
    refresh()
def utility_render_quick(self,parent):
    actions=[('Market prices',self.ui_market),('Add a quest',self.open_add_dialog),('Set your location',self.choose_map),('Sync from game',self.sync_from_game),('Farming watchlist',self.ui_watchlist),('Training suggestions',lambda:self.set_tab('train')),('Party quest guides',lambda:self.set_tab('pq')),('Trainer',self.toggle_trainer),('Profile & appearance',self.ui_settings)]
    for title,action in actions:ui_button(parent,title,action).pack(fill='x',padx=18,pady=5)

def install_tools(cls):
    for name,value in list(globals().items()):
        if name.startswith('utility_') and callable(value):setattr(cls,name,value)
    cls.ui_tools=utility_open

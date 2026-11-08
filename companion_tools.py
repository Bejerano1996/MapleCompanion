from widgets import font_size
"""Companion utility screens adapted to Umbrale's public App APIs."""
import tkinter as tk
import time
from widgets import C,FONT,label,ScrollArea,Tooltip
from companion_widgets import ui_button,ui_card
from companion_feature_model import *
from companion_planner_model import *
from session_rewards import RewardTracker,session_token,apply_rewards
from session_reader import capture_rewards,capture_training
from training_accounting import TrainingAccountant
from game_sync import window_rect

def ui_tools_indicator(self):
    due=sum(1 for timer in self.state.get('utility_timers',[]) if utility_timer_status(timer)[1])
    if hasattr(self,'tools_btn'):
        self.tools_btn.config(fg=C['gold'] if due else C['text'])
        tip=getattr(self.tools_btn,'_companion_tooltip',None)
        if tip:tip.text='Companion tools · Ctrl+K'+(f' · {due} reminders due' if due else '')

def utility_tick(self):
    self.context_poll()
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
    self.render_levelup()
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
        self._reward_tracker=RewardTracker();self._training_accountant=TrainingAccountant();self._reward_token=token;self._training_last_hud=0
        from training_yield import YieldLearner
        self._yield_learner=YieldLearner()
    if getattr(self,'_reward_busy',False) or time.monotonic()-getattr(self,'_reward_last_poll',0)<.12:return
    self._reward_last_poll=time.monotonic()
    windows=[self.root]+[w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel)]
    hide=[window_rect(w) for w in windows if w.winfo_viewable()]
    tracker=self._reward_tracker;accountant=self._training_accountant;self._reward_busy=True
    gain_context=self.training_gain_context()
    read_status=time.monotonic()-getattr(self,'_training_last_hud',0)>=1
    if read_status:self._training_last_hud=time.monotonic()
    read_wallet=bool(session.get('wallet_auto')) and time.monotonic()-getattr(self,'_wallet_last_poll',0)>=3
    if read_wallet:self._wallet_last_poll=time.monotonic()
    def loaded(result):
        events=result.get('events') if isinstance(result,dict) else result
        reading=result.get('character') if isinstance(result,dict) else None
        self._reward_busy=False
        current=self.state['utility_session']
        if session_token(current)!=token or getattr(self,'_reward_token',None)!=token:return
        if events and any(kind=='bonus' for kind,amount in events):self._training_party_seen_at=time.time()
        self._reward_status='Game or reward area unavailable' if events is None else ('Reading reward log · some amounts unclear' if any(amount is None for kind,amount in events) else 'Reading reward log') if events else 'Waiting for visible rewards'
        if getattr(events,'partial',False):self._reward_status+=' · partially covered; visible rows only'
        previous_character=accountant.character
        changed=accountant.feed(current,token,events,reading,time.monotonic())
        wallet=result.get('wallet') if isinstance(result,dict) else None
        if wallet is not None and current.get('wallet_auto'):
            from wallet_model import checkpoint
            if getattr(self,'_wallet_scope',None)!=token:
                current.update(wallet_start=wallet,wallet_offset=current.get('wallet_net',0))
                if current.get('wallet_elapsed_anchor') is None:current['wallet_elapsed_anchor']=utility_session_elapsed(current)
                self._wallet_scope=token
            current=checkpoint(current,wallet,current.get('wallet_start') if current.get('wallet_start') is not None else wallet)
            current['wallet_read_at']=time.time();self.state['utility_session']=current;changed=True
        if reading and accountant.character is reading:
            self.training_accept_character(reading)
            changed=True
        # A background capture may finish after the target, map or party changes.
        # Keep its session totals, but never calibrate the new context with it.
        if gain_context!=self.training_gain_context():
            from training_yield import YieldLearner
            self._yield_learner=YieldLearner()
        elif reading and accountant.character is reading:
            if self.training_buffer_yield(accountant.last_delta,previous_character,reading):self.render_levelup()
        else:self.training_buffer_yield(accountant.last_delta)
        if changed:self.save_state()
        if getattr(self,'_utility_refresh',None):self._utility_refresh()
        self.root.after(120,self.utility_poll_rewards)
    def failed(error):
        self._reward_busy=False;self._reward_status='Reader unavailable · '+str(error)[:90]
    self.run_bg(lambda:capture_training(hide,read_status,read_wallet=True) if read_wallet else capture_training(hide,read_status),loaded,on_error=failed)

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
    if self.state.get('training_auto_context',True) and hasattr(self,'_training_context'):
        context=self._training_context
        known=known and context.get('map_readable') and context.get('map')==current and time.time()-context.get('map_at',0)<=20
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
    metrics = label(card, '', fg='muted', bg='card', size=10, justify='left', anchor='w',wraplength=380)
    metrics.pack(fill='x', padx=12, pady=5)
    map_label=label(card,'',fg='muted',bg='card',size=9,wraplength=390,justify='left')
    map_label.pack(fill='x',padx=12,pady=(0,4))
    self.training_session_counter(card)
    controls = tk.Frame(card, bg=C['card'])
    controls.pack(fill='x', padx=12, pady=8)
    def toggle():
        utility_track_current_map(self)
        self.state['utility_session'] = utility_session_toggle(self.state['utility_session'])
        self.save_state()
        refresh()
        self.utility_poll_rewards()
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
    message._training_tip=Tooltip(message,'EXP-bar totals include party, quests and losses. Party and mesos amounts come from visible notices and may be partial. Clear mesos notices use high-confidence OCR; weaker readings require two matching reads. Kills are EXP-event estimates, including party/shared rewards. Covered or unclear log messages are not guessed.')
    auto=tk.BooleanVar(value=s.get('auto_rewards',True))
    def auto_changed():
        self.state['utility_session']['auto_rewards']=auto.get();self._reward_token=None;self.save_state();refresh()
    tk.Checkbutton(parent,text='Auto read game',variable=auto,command=auto_changed,bg=C['bg'],fg=C['text'],selectcolor=C['card']).pack(anchor='w',padx=20)
    def notice_mode():
        current=self.state['utility_session']
        if current.get('money_mode')=='wallet':
            current.update(mesos=0,cost=0,money_elapsed_anchor=utility_session_elapsed(current))
        current.update(wallet_auto=False,money_mode='notices')
        self._reward_token=None;self.save_state();refresh();self.utility_poll_rewards()
    ui_button(parent,'Mesos · read pickup notices',notice_mode,compact=True,tip='Count gained mesos messages in the lower-right game log; inventory can stay closed').pack(anchor='w',padx=20,pady=4)
    def wallet_dialog():
        from wallet_model import checkpoint
        dialog=self.ui_dialog('Mesos · wallet checkpoints')
        current=self.state['utility_session']
        label(dialog,'Wallet net = current balance − starting balance',fg='gold',wraplength=410).pack(padx=16,pady=12)
        label(dialog,'Enter balances shown in your inventory. Includes spending, trades and storage transfers. Checkpoints update only when you apply them.',fg='muted',wraplength=410,justify='left').pack(padx=16,pady=4)
        initial=utility_entry(dialog,'STARTING WALLET BALANCE',current.get('wallet_start',''))
        latest=utility_entry(dialog,'CURRENT WALLET BALANCE',current.get('wallet_current',''))
        error=label(dialog,'',fg='red',wraplength=400);error.pack(padx=16,pady=6)
        def save_wallet():
            try:updated=checkpoint(dict(self.state['utility_session'],wallet_offset=0,wallet_auto=False,wallet_elapsed_anchor=0),latest.get(),initial.get())
            except ValueError as exc:error.config(text=str(exc));return
            self.state['utility_session']=updated;self.save_state();refresh();dialog.destroy()
        ui_button(dialog,'Apply wallet checkpoint',save_wallet,primary=True).pack(fill='x',padx=16,pady=12)
        def start_wallet():
            self.state['utility_session'].update(wallet_auto=True,money_mode='wallet',wallet_start=None,wallet_current=None,wallet_net=0,wallet_offset=0,wallet_elapsed_anchor=None,mesos=0)
            self._wallet_scope=None
            self.save_state();refresh();dialog.destroy();self.utility_poll_rewards()
        ui_button(dialog,'Start automatic wallet reading',start_wallet,tip='Keep Item Inventory open in the upper-right of the game; net balance starts at the first verified reading').pack(fill='x',padx=16,pady=8)
    ui_button(parent,'Mesos · wallet checkpoints',wallet_dialog,compact=True,tip='Measure net balance directly; avoids missed loot notices').pack(anchor='w',padx=20,pady=4)
    form = ui_card(parent)
    fields = {key: utility_entry(form, title, s.get(key, 0)) for key, title in
              [('kills', 'KILLS ≈'), ('exp', 'EXP GAINED'), ('mesos', 'MESOS OBSERVED'), ('cost', 'POTIONS / OTHER COSTS')]}
    note = utility_entry(form, 'SESSION NOTE', s.get('note', ''))
    feedback = label(form, '', fg='red', bg='card', size=9, wraplength=390)
    feedback.pack(fill='x', padx=12)
    def apply():
        try:
            values = {key: int(utility_number(var.get())) for key, var in fields.items() if key=='cost' or (not self.state['utility_session'].get('auto_rewards',True) and not (key=='mesos' and self.state['utility_session'].get('money_mode')=='wallet'))}
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
        money_label='wallet net' if current.get('money_mode')=='wallet' else 'mesos from notices ≈'
        metrics.config(text=f"{current.get('exp',0):,} EXP · party +{current.get('party_exp',0):,} seen\n≈{current.get('kills',0):,} kills · {current.get('mesos',0):,} {money_label}\n{rates['exp_hour']:,.0f} EXP/h · {rates['net_hour']:,.0f} net mesos/h")
        automatic=current.get('auto_rewards',True)
        auto.set(automatic)
        for key in ('kills','exp','mesos'):
            readonly=automatic or (key=='mesos' and current.get('money_mode')=='wallet')
            if readonly:fields[key].set(str(current.get(key,0)))
            for widget in form.winfo_children():
                if isinstance(widget,tk.Entry) and str(widget.cget('textvariable'))==str(fields[key]):widget.config(state='readonly' if readonly else 'normal',readonlybackground=C['header_dark'])
        if automatic:message.config(text=(getattr(self,'_reward_status','Start to read the reward log') if current.get('running_since') is not None else 'Paused · press Start / resume')+' · Kills ≈ EXP events, including party. Keep the reward log visible.')
        else:message.config(text='Manual mode · enter totals and save.')
        if current.get('map_unattributed'):
            map_text='Map data incomplete · excluded from map comparison'
        elif current.get('map_mixed'):
            map_text='Multiple maps · excluded from map comparison'
        elif current.get('map_id'):
            map_text='Session map: '+str(current.get('map_name') or current['map_id'])
        else:map_text='The session map is recorded when you start.'
        map_label.config(text=self.context_summary() if self.state.get('training_auto_context',True) else map_text)
        target_label=getattr(self,'_training_session_forecast_label',None)
        if target_label is not None and target_label.winfo_exists():target_label.config(text=self.training_forecast_text())
        source=current.get('exp_source','Reward log · observed') if automatic else 'Manual totals'
        quality=getattr(self,'_reward_status','Waiting for game reading')
        accountant=getattr(self,'_training_accountant',None)
        last=accountant.ledger.last_at if accountant else None
        age=time.monotonic()-last if last is not None else None
        freshness=f'EXP read {int(age)}s ago' if age is not None else 'Waiting for EXP baseline'
        paused='Paused · ' if current.get('running_since') is None else ''
        message.config(text=paused+source+' · '+freshness+'\n'+quality+' · Mesos / kills: observed estimates' if automatic else 'Manual totals · costs and notes saved separately')
        if current.get('money_mode')=='wallet':
            wallet_at=current.get('wallet_read_at')
            wallet_status=(f'Wallet read {int(time.time()-wallet_at)}s ago' if wallet_at else 'Waiting for wallet baseline') if current.get('wallet_auto') else 'Manual wallet checkpoint'
            message.config(text=paused+source+' · '+freshness+'\n'+wallet_status+' · net incl. spending / transfers')
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
            if row.get('log_gap_sessions'):
                label(card,f"Partial log in {row['log_gap_sessions']} sessions · mesos may be incomplete",bg='card',fg='muted',size=8,wraplength=375).pack(anchor='w',padx=12,pady=(0,5))
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


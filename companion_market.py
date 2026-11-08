from widgets import font_size
import tkinter as tk
from widgets import C,FONT,label,ScrollArea
from companion_widgets import ui_button,ui_card
"""Independent public market client. No game/profile information is sent."""
import urllib.request as market_request
import urllib.parse as market_parse
import urllib.error as market_error
import threading as market_threading
import queue as market_queue
import datetime as market_datetime
import time as market_time
import json as market_json
import math as market_math
import email.utils as market_email

MARKET_ORIGIN = 'https://maplestory.watch'

def market_retry_delay(error, now=None):
    fallback = 300 if isinstance(error, market_error.HTTPError) and error.code == 429 else 60
    if not isinstance(error, market_error.HTTPError):
        return fallback
    value = error.headers.get('Retry-After') if error.headers else None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            seconds = market_email.parsedate_to_datetime(value).timestamp() - (market_time.time() if now is None else now)
        except (TypeError, ValueError, AttributeError, OverflowError):
            return fallback
    return max(fallback, seconds) if market_math.isfinite(seconds) else fallback

def market_valid_price(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and market_math.isfinite(value) and value >= 0

def market_payload(data, name=None):
    key = 'items' if name is None else 'listings'
    if not isinstance(data, dict) or not isinstance(data.get(key), list):
        raise ValueError('Unexpected market response')
    result = dict(data)
    result[key] = [dict(row) for row in data[key] if isinstance(row, dict) and (name is not None or isinstance(row.get('name'), str))]
    if data[key] and not result[key]:
        raise ValueError('Market response contains no valid records')
    if name is None:
        for row in result[key]:
            if not isinstance(row.get('range'), list) or len(row['range']) != 2:
                row['range'] = []
    return result

def market_fetch(name=None):
    path = '/api/items' if name is None else '/api/item?' + market_parse.urlencode({'name': name})
    request = market_request.Request(MARKET_ORIGIN + path, headers={'Accept': 'application/json', 'User-Agent': 'MapleCompanion/5.3.2'})
    with market_request.urlopen(request, timeout=15) as response:
        raw = response.read(4000001)
    if len(raw) > 4000000:
        raise ValueError('Market response exceeds size limit')
    data = market_json.loads(raw)
    return market_payload(data, name)

def market_money(value):
    return f'{value:,.0f}' if market_valid_price(value) else 'Unavailable'

def market_stamp(value):
    try:
        return market_datetime.datetime.fromtimestamp(float(value)).strftime('%d %b %H:%M:%S')
    except (ValueError, TypeError, OverflowError, OSError):
        return 'Unknown'

def market_listings(data):
    # Keep source observations, but collapse identical rows; they are not stock counts.
    unique = {}
    for row in data.get('listings', []):
        if not isinstance(row, dict) or row.get('soldOut') or row.get('closed'):
            continue
        price = row.get('unit')
        if not market_valid_price(price):
            continue
        key = tuple(str(row.get(k)) for k in ('seller', 'map', 'channel', 'unit', 'bundle', 'pos'))
        def timestamp(record):
            value = record.get('seen')
            return value if market_valid_price(value) else 0
        if key not in unique or timestamp(row) > timestamp(unique[key]):
            unique[key] = row
    return sorted(unique.values(), key=lambda row: row['unit'])

def market_open(self):
    existing = getattr(self, '_market_window', None)
    if existing and existing.winfo_exists():
        existing.lift()
        return
    w = self.ui_dialog('Market · MapleStory Watch')
    self._market_window = w
    w.geometry('530x680')
    w.minsize(440, 420)
    w.resizable(True, True)
    label(w, 'Market prices', size=18, bold=True).pack(anchor='w', padx=18)
    label(w, 'Mesos per item · Source: maplestory.watch', fg='muted', size=9).pack(anchor='w', padx=18)
    ui_button(w, 'MesoWatch · website lookup & saved quotes ↗', self.ui_mesowatch, compact=True).pack(fill='x', padx=18, pady=6)
    status = label(w, 'Connecting…', fg='muted', size=9, wraplength=450, justify='left')
    status.pack(fill='x', padx=18, pady=8)
    controls = tk.Frame(w, bg=C['bg']); controls.pack(fill='x', padx=18)
    query = tk.StringVar()
    self._market_search_query = query
    entry = tk.Entry(controls, textvariable=query, font=(FONT, font_size(11)))
    entry.pack(side='left', fill='x', expand=True, ipady=5)
    area = ScrollArea(w); area.pack(fill='both', expand=True, padx=12, pady=8)
    inbox = market_queue.Queue()
    state = {'index': None, 'details': {}, 'detail_times': {}, 'selected': None, 'busy': False, 'next': 0, 'error': '', 'received': None}
    self._market_view_state = state

    def render(*unused):
        area.clear(False)
        if state['selected']:
            name = state['selected']
            ui_button(area.inner, '← Search results', back, compact=True).pack(anchor='w', pady=4)
            label(area.inner, name, size=14, bold=True, wraplength=440).pack(anchor='w', pady=8)
            row = next((r for r in (state['index'] or {}).get('items', []) if r.get('name') == name), {})
            card = ui_card(area.inner, pady=5)
            spread = row.get('range') or []
            lines = ['Typical: ' + market_money(row.get('typical')), 'Lowest observed ask: ' + market_money(row.get('lowest'))]
            if len(spread) == 2:
                lines.append('Typical range: ' + market_money(spread[0]) + ' – ' + market_money(spread[1]))
            lines.extend(['Source sales samples: ' + str(row.get('sold', 'Unavailable')), 'Item last seen: ' + market_stamp(row.get('seen'))])
            label(card, '\n'.join(lines), bg='card', size=11, justify='left', wraplength=430).pack(fill='x', padx=12, pady=12)
            detail = state['details'].get(name)
            if detail is None:
                label(area.inner, 'Shop observations unavailable. Refresh to retry.' if state['error'] else 'Loading shop observations…', fg='muted').pack(pady=12)
            else:
                listings = market_listings(detail)
                label(area.inner, 'Shop details fetched: ' + market_stamp(state['detail_times'].get(name)), size=9, fg='muted').pack(anchor='w')
                label(area.inner, 'Observed shops · lowest unit price first', bold=True, size=10).pack(anchor='w', pady=8)
                label(area.inner, 'Scanned offers may have changed. Verify in game. Repeated identical observations are collapsed.', size=9, fg='muted', wraplength=440, justify='left').pack(fill='x')
                if not listings:
                    label(area.inner, 'No available shop observations.', fg='muted').pack(pady=12)
                for listing in listings[:40]:
                    card = ui_card(area.inner, pady=3)
                    text = f"{market_money(listing.get('unit'))} mesos / item\n{listing.get('seller', '?')} · CH {listing.get('channel', '?')} · {listing.get('map', '?')}\nLast seen: {market_stamp(listing.get('seen'))}"
                    label(card, text, bg='card', size=10, wraplength=430, justify='left').pack(fill='x', padx=12, pady=10)
        else:
            rows = (state['index'] or {}).get('items', [])
            term = query.get().strip().casefold()
            matched = [r for r in rows if isinstance(r, dict) and term in str(r.get('name', '')).casefold()]
            label(area.inner, f'{len(matched)} items · showing up to 60', fg='muted', size=9).pack(anchor='w', pady=6)
            for row in matched[:60]:
                title = str(row.get('name', '?'))
                button = ui_button(area.inner, title + '\nTypical: ' + market_money(row.get('typical')) + ' mesos', lambda n=title: select(n))
                button.config(wraplength=390)
                button.pack(fill='x', pady=3)
            if not matched:
                label(area.inner, 'No matching items.' if state['index'] is not None else 'Waiting for market data…', fg='muted').pack(pady=18)
        area.commit()

    def back():
        state['selected'] = None; render()

    def select(name):
        state['selected'] = name; render()
        if not state['error']:
            state['next'] = 0
        refresh()

    def refresh():
        if state['busy'] or market_time.monotonic() < state['next']:
            return
        state['busy'] = True
        name = state['selected']
        status.config(text='Refreshing public market data…')
        def worker():
            try:
                index = market_fetch()
                detail = market_fetch(name) if name else None
                inbox.put((True, name, index, detail))
            except Exception as exc:
                inbox.put((False, name, str(exc)[:200], market_retry_delay(exc)))
        market_threading.Thread(target=worker, daemon=True).start()

    def poll():
        if not w.winfo_exists():
            return
        try:
            ok, name, value, detail = inbox.get_nowait()
            state['busy'] = False
            state['next'] = market_time.monotonic() + (10 if ok else detail)
            if ok:
                state['index'] = value
                if name is not None:
                    state['details'][name] = detail
                    state['detail_times'][name] = market_time.time()
                state['received'] = market_time.time(); state['error'] = ''
                if state['selected'] and state['selected'] != name and state['selected'] not in state['details']:
                    state['next'] = 0
                    refresh()
            else:
                state['error'] = value
            render()
        except market_queue.Empty:
            pass
        if not state['busy']:
            if state['error']:
                text = ('Cached observations · ' if state['index'] else 'Market unavailable · ') + state['error']
            elif state['index'] is not None:
                text = 'Source update: ' + market_stamp(state['index'].get('at')) + ' · Fetched: ' + market_stamp(state['received']) + ' · Auto refresh: 60s'
                maintenance = state['index'].get('maintenance')
                if isinstance(maintenance, dict) and maintenance.get('started') and not maintenance.get('ended'):
                    text += '\nSource maintenance in progress'
            else:
                text = 'Waiting for market data…'
            status.config(text=text)
            if market_time.monotonic() >= state['next'] and (state['received'] is None or market_time.time() - state['received'] >= 60):
                refresh()
        state['poll_job'] = w.after(200, poll)

    ui_button(controls, 'Refresh', refresh, compact=True).pack(side='right', padx=(6, 0))
    ui_button(w, 'Open source website ↗', lambda: __import__('webbrowser').open(MARKET_ORIGIN + '/market'), compact=True).pack(pady=(0, 10))
    query_trace = query.trace_add('write', render)
    def cleanup(event):
        if event.widget != w:
            return
        query.trace_remove('write', query_trace)
        if state.get('poll_job'):
            try:
                w.after_cancel(state['poll_job'])
            except tk.TclError:
                pass
            state['poll_job'] = None
    w.bind('<Destroy>', cleanup, add='+')
    refresh(); poll(); entry.focus_set()



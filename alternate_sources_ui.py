"""Source-attributed discovery without guessing game IDs or quest requirements."""
import tkinter as tk
import webbrowser
import widgets
from widgets import C, label, ScrollArea
from alternate_sources import AlternateCatalogs, PROVIDERS


def open_sources(app, query_text=''):
    from meowdb import CACHE_DIR
    existing = getattr(app, '_alternate_sources_window', None)
    if existing is not None and existing.winfo_exists():
        if query_text:
            existing._source_query.set(query_text)
        existing.lift()
        return existing
    if not hasattr(app, 'alternate_catalogs'):
        app.alternate_catalogs = getattr(app.db, 'reference_catalogs', None) or AlternateCatalogs(CACHE_DIR)
    catalogs = app.alternate_catalogs
    window = app.ui_dialog('Additional quest sources', width=620, height=540)
    app._alternate_sources_window = window
    label(window, 'CCPLZ + MapleStory Classic', bold=True).pack(anchor='w', padx=12, pady=8)
    label(window, 'Reference catalogs · open a quest to see full requirements.\n'
          'These records do not change your tracked quests, GPS or EXP calculations.',
          fg='muted', justify='left', wraplength=580).pack(anchor='w', padx=12)
    top = tk.Frame(window, bg=C['bg'])
    top.pack(fill='x', padx=12, pady=8)
    query = tk.StringVar(window, value=query_text)
    window._source_query = query
    widgets.entry(top, query).pack(side='left', fill='x', expand=True)
    filters = tk.Frame(window, bg=C['bg'])
    filters.pack(fill='x', padx=12, pady=(0, 5))
    level = max(1, min(250, int(app.state.get('level') or 1)))
    near = tk.BooleanVar(window, value=False)
    toggle = tk.Checkbutton(filters, text=f'Near Lv {level}', variable=near, bg=C['bg'], fg=C['text'],
                            activebackground=C['bg'], selectcolor=C['card'],
                            font=(widgets.FONT, widgets.font_size(9)))
    toggle.pack(side='left')
    widgets.Tooltip(toggle, f'Minimum quest level {max(1, level-10)}–{level}. Prerequisites and class requirements may still apply.')
    status = label(window, 'Choose Refresh to load both catalogs.', fg='muted', wraplength=580, justify='left')
    status.pack(anchor='w', padx=12)
    area = ScrollArea(window)
    area.pack(fill='both', expand=True, padx=12, pady=8)
    pool = []
    shown = []
    render_signature = None

    def open_row(index):
        if index < len(shown):
            webbrowser.open(shown[index]['url'])

    def render(*unused):
        nonlocal shown, render_signature
        if not window.winfo_exists():
            return
        rows = catalogs.search(query.get(), (max(1, level-10), level) if near.get() else None)
        summary = ' · '.join(PROVIDERS[key][0] + ': ' + str(len(catalogs.rows.get(key, []))) +
                             ' (' + catalogs.status.get(key, 'Not loaded') + ')' for key in PROVIDERS)
        summary += f'\n{len(rows)} results' + (' · narrow the search to see more' if len(rows)>80 else '')
        if status.cget('text') != summary:
            status.configure(text=summary)
        # Bound Tk work; search narrows long catalogs rather than freezing the overlay.
        shown = rows[:80]
        signature = tuple((row['url'],row['name'],row['level'],row['exp']) for row in shown)
        if signature == render_signature:
            return
        render_signature = signature
        while len(pool) < len(shown):
            index = len(pool)
            line = tk.Frame(area.inner, bg=C['card'])
            title = widgets.button(line, '', lambda index=index: open_row(index), bg='card',
                                   anchor='w', wraplength=540, justify='left')
            title.pack(fill='x')
            info = label(line, '', fg='muted', bg='card')
            info.pack(anchor='w', padx=7)
            pool.append((line,title,info))
        for index, (line, title_widget, info_widget) in enumerate(pool):
            if index >= len(shown):
                line.pack_forget()
                continue
            row = shown[index]
            if not line.winfo_manager():
                line.pack(fill='x', pady=3)
            title = row['name'] + ' · Lv ' + str(row['level'])
            if title_widget.cget('text') != title:
                title_widget.configure(text=title)
            exp = 'EXP not listed' if row['exp'] is None else f"{row['exp']:,} EXP"
            info = PROVIDERS[row['provider']][0] + ' · ' + exp
            if info_widget.cget('text') != info:
                info_widget.configure(text=info)
        area.canvas.yview_moveto(0)
    busy = False

    def refresh():
        nonlocal busy
        if busy:
            return
        busy = True
        status.configure(text='Loading two public catalogs in the background…')
        def finished(result):
            nonlocal busy
            busy = False
            if hasattr(app, 'reference_catalogs_updated'):
                app.reference_catalogs_updated()
            render()
        def failed(error):
            nonlocal busy
            busy = False
            if window.winfo_exists():
                status.configure(text='Refresh failed · saved catalogs retained: '+str(error))
        app.run_bg(lambda: catalogs.refresh(force=True), finished, on_error=failed)

    widgets.button(top, 'Refresh', refresh).pack(side='right', padx=(8, 0))
    query_trace = query.trace_add('write', render)
    near_trace = near.trace_add('write', render)
    def close(event):
        if event.widget != window:
            return
        query.trace_remove('write', query_trace)
        near.trace_remove('write', near_trace)
        if getattr(app, '_alternate_sources_window', None) is window:
            app._alternate_sources_window = None
    window.bind('<Destroy>', close, add='+')
    if catalogs.rows:
        render()
    return window

"""Source-attributed discovery without guessing game IDs or quest requirements."""
import tkinter as tk
import webbrowser
import widgets
from widgets import C, label, ScrollArea
from alternate_sources import AlternateCatalogs, PROVIDERS


def open_sources(app):
    from meowdb import CACHE_DIR
    if not hasattr(app, 'alternate_catalogs'):
        app.alternate_catalogs = AlternateCatalogs(CACHE_DIR)
    catalogs = app.alternate_catalogs
    window = app.ui_dialog('Additional quest sources')
    window.geometry('620x540')
    label(window, 'CCPLZ + MapleStory Classic', bold=True).pack(anchor='w', padx=12, pady=8)
    label(window, 'Reference catalogs · open a quest to see full requirements.\n'
          'These records do not change your tracked quests, GPS or EXP calculations.',
          fg='muted', justify='left', wraplength=580).pack(anchor='w', padx=12)
    top = tk.Frame(window, bg=C['bg'])
    top.pack(fill='x', padx=12, pady=8)
    query = tk.StringVar(window)
    widgets.entry(top, query).pack(side='left', fill='x', expand=True)
    status = label(window, 'Choose Refresh to load both catalogs.', fg='muted', wraplength=580, justify='left')
    status.pack(anchor='w', padx=12)
    area = ScrollArea(window)
    area.pack(fill='both', expand=True, padx=12, pady=8)

    def render(*unused):
        if not window.winfo_exists():
            return
        for child in area.inner.winfo_children():
            child.destroy()
        rows = catalogs.search(query.get())
        summary = ' · '.join(PROVIDERS[key][0] + ': ' + str(len(catalogs.rows.get(key, []))) +
                             ' (' + catalogs.status.get(key, 'Not loaded') + ')' for key in PROVIDERS)
        status.configure(text=summary)
        # Bound Tk work; search narrows long catalogs rather than freezing the overlay.
        for row in rows[:80]:
            line = tk.Frame(area.inner, bg=C['card'])
            line.pack(fill='x', pady=3)
            title = row['name'] + ' · Lv ' + str(row['level'])
            widgets.button(line, title, lambda url=row['url']: webbrowser.open(url), bg='card',
                           anchor='w', wraplength=540, justify='left').pack(fill='x')
            exp = 'EXP not listed' if row['exp'] is None else f"{row['exp']:,} EXP"
            label(line, PROVIDERS[row['provider']][0] + ' · ' + exp, fg='muted', bg='card').pack(anchor='w', padx=7)
        if len(rows) > 80:
            label(area.inner, f'{len(rows)} results · type to narrow the list', fg='muted').pack()
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
            render()
        app.run_bg(catalogs.refresh, finished)

    widgets.button(top, 'Refresh', refresh).pack(side='right', padx=(8, 0))
    query.trace_add('write', render)
    if catalogs.rows:
        render()
    return window

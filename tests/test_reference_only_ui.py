"""Fresh-install reference mode; own Tk windows and synthetic OCR only."""
from pathlib import Path
import json
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

import app
from meowdb import MeowDB
from alternate_sources import parse_catalog
from companion_widgets import ui_walk_widgets


class NoHotkey:
    def __init__(self,*args,**kwargs): pass
    def start(self): pass


class ReferenceOnlyTests(unittest.TestCase):
    def test_missing_primary_cache_keeps_journal_and_displays_live_reference(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            state_path=Path(folder)/'state.json'
            fixture=dict(auto_sync=True,auto_on_v2=True,active=['unavailable-old-id'],
                         tracked=['unavailable-old-id'],progress={'unavailable-old-id':{'0':7}},
                         done={},completed=[])
            state_path.write_text(json.dumps(fixture),encoding='utf-8')
            db=MeowDB(folder)
            reference_rows=parse_catalog('ccplz','<li><a href="/quests/new">Brand New Quest</a><span>Level 39, from NPC, 120 EXP</span></li>')
            root=tk.Tk();root.withdraw();errors=[]
            root.report_callback_exception=lambda kind,value,trace:errors.append(str(value))
            try:
                with patch.object(app,'STATE_FILE',str(state_path)),patch.object(app,'MeowDB',return_value=db), \
                     patch.object(app,'HotkeyThread',NoHotkey),patch.object(app.App,'sync_from_game'), \
                     patch.object(app.App,'prefetch'),patch('urllib.request.urlopen',side_effect=AssertionError('unexpected network')):
                    a=app.App(root)
                    until=time.monotonic()+.2
                    while time.monotonic()<until:
                        root.update();time.sleep(.005)
                    self.assertFalse(a.db.quests)
                    unavailable=[w.cget('text') for w in ui_walk_widgets(a.scroll.inner) if isinstance(w,(tk.Label,tk.Button))]
                    self.assertIn('Quest sources',unavailable)
                    db.reference_catalogs.rows['ccplz']=reference_rows
                    a.reference_catalogs_updated();root.update()
                    texts=[w.cget('text') for w in ui_walk_widgets(a.scroll.inner) if isinstance(w,(tk.Label,tk.Button))]
                    self.assertIn('Quest reference mode',texts)
                    self.assertIsNotNone(a._auto_job)
                    before=a._snapshot()
                    a._on_synced(dict(auto=False,full=True,regions=[(100,100,300,300)],
                                      references=[dict(name='Brand New Quest',sources=db.reference_catalogs.rows['ccplz'])],
                                      quests=[],tracked=[],progress={},window=True))
                    root.update()
                    texts=[w.cget('text') for w in ui_walk_widgets(a.scroll.inner) if isinstance(w,(tk.Label,tk.Button))]
                    self.assertIn('Brand New Quest',texts)
                    self.assertIn('CCPLZ: 120 EXP',texts)
                    self.assertEqual(a._snapshot(),before)
                    a._on_synced(None)
                    self.assertFalse(a.visible_references.visible)
                    self.assertEqual(a._snapshot(),before)
                    self.assertEqual(errors,[])
            finally:
                for job in root.tk.call('after','info'):
                    root.tk.call('after','cancel',job)
                root.destroy()


if __name__=='__main__': unittest.main()

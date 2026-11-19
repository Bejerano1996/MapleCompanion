from pathlib import Path
import json
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

import app


class NoHotkey:
    def __init__(self,*args,**kwargs):pass
    def start(self):pass


class ClosePersistenceTests(unittest.TestCase):
    def test_native_window_close_saves_pending_quest_changes(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            state=Path(folder)/'state.json'
            state.write_text(json.dumps(dict(auto_sync=False,auto_on_v2=True,active=['10306'],
                                            tracked=['10306'],progress={'10306':{'0':1}})),encoding='utf-8')
            root=tk.Tk();root.withdraw()
            try:
                with patch.object(app,'STATE_FILE',str(state)),patch.object(app,'HotkeyThread',NoHotkey), \
                     patch.object(app.App,'run_bg'),patch.object(app.App,'sync_from_game'),patch.object(app.App,'prefetch'):
                    a=app.App(root)
                    a.state['progress']['10306']['0']=7
                    command=root.protocol('WM_DELETE_WINDOW')
                    self.assertTrue(command,'Window close must use the same save path as Quit')
                    for job in root.tk.call('after','info'):root.tk.call('after','cancel',job)
                    root.tk.call(command)
                self.assertEqual(json.loads(state.read_text())['progress']['10306']['0'],7)
            finally:
                try:root.destroy()
                except tk.TclError:pass


if __name__=='__main__':unittest.main()

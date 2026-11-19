import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app


class QuestCaptureFreshnessTests(unittest.TestCase):
    def subject(self):
        root = SimpleNamespace(winfo_children=lambda: [], winfo_viewable=lambda: False,
                               after=lambda *args: scheduled.append(args))
        scheduled = []
        subject = SimpleNamespace(syncing=False, resetting=False, root=root, focus=None,
                                  db=SimpleNamespace(quests={'quest': {}}),
                                  state={'auto_sync': True, 'active':['quest'], 'tracked':['quest'],
                                         'completed':[], 'done':{}, 'progress':{}},
                                  statuses=[], received=[], callbacks=[], _reads={('quest','old'):('old',2)})
        subject.set_status=lambda *args: subject.statuses.append(args)
        subject.run_bg=lambda work, loaded, on_error: subject.callbacks.append(loaded)
        subject._on_synced=lambda result: subject.received.append(result)
        subject.sync_from_game=lambda **kwargs: None
        subject.scheduled=scheduled
        return subject

    def test_expired_quest_result_cannot_mutate_journal_and_retries(self):
        for delay in (15.001, 30, 120):
            subject=self.subject()
            with patch.object(app.time, 'monotonic', return_value=100):
                app.App.sync_from_game(subject, auto=True)
            with patch.object(app.time, 'monotonic', return_value=100+delay):
                subject.callbacks.pop()({'auto':True,'quests':['old']})
            self.assertEqual(subject.received, [])
            self.assertFalse(subject.syncing)
            self.assertTrue(subject.scheduled)
            self.assertEqual(subject._reads, {})

    def test_timely_result_still_applies_once(self):
        for delay in (0, 14.999, 15):
            subject=self.subject()
            with patch.object(app.time, 'monotonic', return_value=100):
                app.App.sync_from_game(subject, auto=True)
            with patch.object(app.time, 'monotonic', return_value=100+delay):
                subject.callbacks.pop()({'auto':True,'quests':['new']})
            self.assertEqual(subject.received, [{'auto':True,'quests':['new']}])

    def test_manual_journal_edit_invalidates_pending_scan(self):
        subject=self.subject()
        with patch.object(app.time, 'monotonic', return_value=100):
            app.App.sync_from_game(subject, auto=True)
            subject.state['active'].clear()
            subject.callbacks.pop()({'auto':True,'quests':['old']})
        self.assertEqual(subject.received, [])
        self.assertEqual(subject.state['active'], [])
        self.assertFalse(subject.syncing)

    def test_manual_edit_does_not_queue_a_second_manual_scan(self):
        subject=self.subject()
        with patch.object(app.time,'monotonic',return_value=100):
            app.App.sync_from_game(subject,auto=False)
            subject.state['active'].clear()
            subject.callbacks.pop()({'auto':False,'quests':['old']})
        self.assertEqual(subject.received,[])
        self.assertEqual(subject.scheduled,[])

    def test_new_reset_session_cannot_accept_old_scan(self):
        subject=self.subject()
        with patch.object(app.time, 'monotonic', return_value=100):
            app.App.sync_from_game(subject, auto=True)
            subject.resetting={'seen':[]}
            subject.callbacks.pop()({'auto':True,'quests':['old']})
        self.assertEqual(subject.received, [])
        self.assertEqual(subject.resetting['seen'], [])

    def test_turning_auto_off_rejects_inflight_automatic_scan(self):
        subject=self.subject()
        with patch.object(app.time,'monotonic',return_value=100):
            app.App.sync_from_game(subject,auto=True)
            subject.state['auto_sync']=False
            subject.callbacks.pop()({'auto':True,'quests':['old']})
        self.assertEqual(subject.received,[])
        self.assertEqual(subject.scheduled,[])
        self.assertFalse(subject.syncing)

    def test_auto_restart_generation_rejects_old_scan_and_requests_fresh_one(self):
        subject=self.subject();subject._sync_generation=0
        with patch.object(app.time,'monotonic',return_value=100):
            app.App.sync_from_game(subject,auto=True)
            subject._sync_generation=2
            subject.callbacks.pop()({'auto':True,'quests':['old']})
        self.assertEqual(subject.received,[])
        self.assertTrue(subject.scheduled)
        self.assertFalse(subject.syncing)


if __name__ == '__main__':
    unittest.main()

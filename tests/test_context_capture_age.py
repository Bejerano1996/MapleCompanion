from types import SimpleNamespace
import unittest
from unittest.mock import patch

from session_rewards import session_token
import training_context as context


class ContextCaptureAgeTests(unittest.TestCase):
    def subject(self):
        session={'id':'fixture','running_since':1,'auto_rewards':True}
        tracker=context.ContextTracker()
        tracker.feed(dict(game=True,map='old',mobs=[23],party_visible=2),90)
        tracker.feed(dict(game=True,map='old',mobs=[23],party_visible=2),98)
        callbacks=[];moves=[];renders=[]
        subject=SimpleNamespace(state={'utility_session':session,'map':'current'},
                                root=SimpleNamespace(winfo_children=lambda:[],winfo_viewable=lambda:False),
                                db=SimpleNamespace(maps={'old':{},'current':{}},monsters={}),
                                _context_scope=session_token(session),_context_tracker=tracker,
                                _training_context=tracker.data.copy(),
                                run_bg=lambda work,loaded,on_error:callbacks.append(loaded),
                                set_location=lambda value:moves.append(value),render_levelup=lambda:renders.append(True))
        return subject,callbacks,moves

    def test_stale_context_cannot_move_player_or_record_monster(self):
        for delay in (0,14.999,15,15.001,30,120):
            subject,callbacks,moves=self.subject()
            with patch.object(context.time,'monotonic',return_value=100),patch.object(context.time,'time',return_value=100):
                context.context_poll(subject)
            with patch.object(context.time,'monotonic',return_value=100+delay),patch.object(context.time,'time',return_value=100+delay):
                callbacks.pop()(dict(game=True,map='old',mobs=[23],party_visible=2,captured_at=100))
            self.assertFalse(subject._context_busy)
            if delay>15:
                self.assertEqual(moves,[])
                self.assertNotIn('observed_monsters',subject.state['utility_session'])
                self.assertEqual(subject._training_context.get('mobs'),[])
            else:
                self.assertEqual(moves,['old'])
                self.assertIn('23',subject.state['utility_session']['observed_monsters'])

    def test_invalid_or_future_wall_timestamp_does_not_establish_context(self):
        for stamp in (float('nan'),float('inf'),101,'invalid'):
            subject,callbacks,moves=self.subject()
            with patch.object(context.time,'monotonic',return_value=100),patch.object(context.time,'time',return_value=100):
                context.context_poll(subject)
                callbacks.pop()(dict(game=True,map='old',mobs=[23],party_visible=2,captured_at=stamp))
            self.assertEqual(moves,[])
            self.assertNotIn('observed_monsters',subject.state['utility_session'])


if __name__=='__main__':unittest.main()

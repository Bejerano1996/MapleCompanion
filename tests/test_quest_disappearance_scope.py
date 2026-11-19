from types import SimpleNamespace
import unittest

import app


class DisappearanceScopeTests(unittest.TestCase):
    def subject(self):
        state = dict(active=['old','new'], tracked=['old','new'], completed=[])
        subject = SimpleNamespace(state=state, _gone={}, focus=[(100,100,200,200)],
                                  db=SimpleNamespace(quests={'old':{'name':'Old Quest','need':[{'count':1}]},
                                                             'new':{'name':'New Quest','need':[{'count':1}]}}))
        subject.done_steps=lambda qid:{0}
        def forget(qid):
            state['active'].remove(qid)
            state['tracked'].remove(qid)
        subject._forget=forget
        return subject

    def test_partial_crop_cannot_prove_turn_in(self):
        subject=self.subject()
        for unused in range(app.GONE_AFTER+2):
            app.App._check_gone(subject, dict(quests=['new'],tracked=['new'],full=False))
        self.assertIn('old',subject.state['active'])
        self.assertEqual(subject.state['completed'],[])
        self.assertIsNone(subject.focus)
        app.App._check_gone(subject,dict(quests=['old','new'],tracked=['old','new'],full=True))
        self.assertNotIn('old',subject._gone)

    def test_full_scan_confirms_real_disappearance(self):
        subject=self.subject()
        for unused in range(app.GONE_AFTER):
            app.App._check_gone(subject,dict(quests=['new'],tracked=['new'],full=False))
        result=app.App._check_gone(subject,dict(quests=['new'],tracked=['new'],full=True))
        self.assertEqual(result,['Old Quest'])
        self.assertIn('old',subject.state['completed'])

    def test_hidden_helper_breaks_consecutive_disappearance_evidence(self):
        subject=self.subject()
        for unused in range(app.GONE_AFTER-1):
            app.App._check_gone(subject,dict(quests=['new'],tracked=['new'],full=True))
        app.App._check_gone(subject,dict(quests=[],tracked=[],full=True))
        result=app.App._check_gone(subject,dict(quests=['new'],tracked=['new'],full=True))
        self.assertEqual(result,[])
        self.assertIn('old',subject.state['active'])


if __name__=='__main__':
    unittest.main()

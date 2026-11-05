import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from training_yield import YieldLearner

class YieldTests(unittest.TestCase):
    def test_notice_window_collects_between_hud_polls(self):
        learner=YieldLearner();key=('mob','map',4,32)
        learner.add_window(key,dict(exp=7,kills=1),0)
        learner.add_window(key,dict(exp=2,party_exp=2),.2)
        window=learner.take_window(key,.5)
        self.assertEqual(window,dict(exp=9,kills=1,party_exp=2))
        self.assertTrue(learner.observe(key,window,9,.5))
        self.assertEqual(learner.take_window(key,.6),{})
    def test_notice_window_expires_and_resets_on_context_change(self):
        learner=YieldLearner();a=('mob','a',4,32);b=('mob','b',4,32)
        learner.add_window(a,dict(exp=9,kills=1),0)
        self.assertEqual(learner.take_window(a,6),{})
        learner.add_window(a,dict(exp=9,kills=1),7)
        self.assertEqual(learner.take_window(b,8),{})
    def test_fresh_reward_after_expired_window_is_retained(self):
        learner=YieldLearner();key=('mob','map',4,32)
        learner.add_window(key,dict(exp=9,kills=1),0)
        learner.add_window(key,dict(exp=10,kills=1),6)
        self.assertEqual(learner.take_window(key,6),dict(exp=10,kills=1,party_exp=0))
    def test_multiple_reward_window_does_not_calibrate(self):
        learner=YieldLearner();key=('mob','map',4,32)
        learner.add_window(key,dict(exp=9,kills=1),0);learner.add_window(key,dict(exp=9,kills=1),.2)
        self.assertFalse(learner.observe(key,learner.take_window(key,.5),18,.5))
    def test_party_bonus_is_included_once(self):
        learner=YieldLearner();signature=('mob','map',4,32)
        for t in range(3):learner.observe(signature,dict(exp=9,party_exp=2,kills=1),9,t)
        self.assertEqual(learner.estimate(signature,3),9)
    def test_multiple_rewards_quests_and_incomplete_bonus_rejected(self):
        learner=YieldLearner();key=('mob','map',None,32)
        for delta,hud in [(dict(exp=18,kills=2),18),(dict(exp=7,kills=1),9),(dict(exp=7,kills=1),107),(dict(exp=7,kills=1),-7)]:
            self.assertFalse(learner.observe(key,delta,hud,1))
        self.assertIsNone(learner.estimate(key,2))
    def test_context_change_and_stale_samples_expire(self):
        learner=YieldLearner();a=('mob','map',4,32);b=('other','map',4,32)
        for t in range(3):learner.observe(a,dict(exp=9,kills=1),9,t)
        self.assertIsNone(learner.estimate(a,48));self.assertIsNone(learner.estimate(b,3))
        learner.observe(b,dict(exp=9,kills=1),9,3)
        self.assertIsNone(learner.estimate(b,3))
    def test_changed_yield_requires_new_agreement(self):
        learner=YieldLearner();key=('mob','map',None,32)
        for t in range(3):learner.observe(key,dict(exp=9,kills=1),9,t)
        learner.observe(key,dict(exp=10,kills=1),10,3)
        self.assertIsNone(learner.estimate(key,3))
        for t in (4,5):learner.observe(key,dict(exp=10,kills=1),10,t)
        self.assertEqual(learner.estimate(key,5),10)
    def test_unknown_target_never_calibrates(self):
        learner=YieldLearner()
        self.assertFalse(learner.observe(('',None,None,32),dict(exp=9,kills=1),9,0))
    def test_split_party_bonus_hud_window_cannot_train_base_only_yield(self):
        learner=YieldLearner();key=('mob','map',None,32)
        for t in (0,2,4):
            learner.observe(key,dict(exp=7,kills=1,party_exp=0),7,t)
            learner.observe(key,dict(exp=2,kills=0,party_exp=2),2,t+.2)
        self.assertIsNone(learner.estimate(key,5))
    def test_late_bonus_refinement_with_unchanged_hud_preserves_good_yield(self):
        learner=YieldLearner();key=('mob','map',None,32)
        for t in range(3):learner.observe(key,dict(exp=9,kills=1,party_exp=2),9,t)
        learner.observe(key,dict(exp=2,kills=0,party_exp=2),0,3)
        self.assertEqual(learner.estimate(key,3),9)
    def test_returning_to_old_map_does_not_revive_calibration(self):
        learner=YieldLearner();a=('mob','a',4,32);b=('mob','b',4,32)
        for t in range(3):learner.observe(a,dict(exp=9,kills=1),9,t)
        self.assertIsNone(learner.estimate(b,3));self.assertIsNone(learner.estimate(a,4))

if __name__=='__main__':unittest.main()

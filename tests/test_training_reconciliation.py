import sys,unittest
import random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from training_accounting import TrainingAccountant
from session_rewards import session_token

class TimingTests(unittest.TestCase):
    def setup_account(self):
        s=dict(id='timing',running_since=1,auto_rewards=True,exp=0,kills=0,mesos=0)
        a=TrainingAccountant();token=session_token(s)
        a.feed(s,token,[],{'level':27,'exp':1000},0)
        return s,a,token
    def test_late_party_bonus_not_added_again_on_stale_bar(self):
        s,a,t=self.setup_account()
        a.feed(s,t,[('exp',7),('bonus',None)],{'level':27,'exp':1009},1)
        a.feed(s,t,[('exp',7),('bonus',2)],None,2)
        a.feed(s,t,[('exp',7),('bonus',2)],None,20)
        self.assertEqual(s['exp'],9)
        self.assertEqual(s['party_exp'],2)
    def test_notice_ahead_of_hud_not_counted_again_later(self):
        s,a,t=self.setup_account();events=[('exp',7),('bonus',2)]
        a.feed(s,t,events,{'level':27,'exp':1000},1)
        a.feed(s,t,events,{'level':27,'exp':1009},2)
        a.feed(s,t,events,None,20)
        self.assertEqual(s['exp'],9)
    def test_net_loss_is_not_undone_by_fallback(self):
        s,a,t=self.setup_account()
        a.feed(s,t,[],{'level':27,'exp':900},1)
        a.feed(s,t,[],None,20)
        self.assertEqual(s['exp'],-100)
    def test_log_leading_unchanged_hud_survives_to_fallback(self):
        s,a,t=self.setup_account();events=[('exp',7),('bonus',2)]
        a.feed(s,t,events,{'level':27,'exp':1000},1)
        a.feed(s,t,events,None,20)
        self.assertEqual(s['exp'],9)
    def test_old_missing_bonus_does_not_swallow_later_base_rewards(self):
        s,a,t=self.setup_account()
        first=[('exp',7),('bonus',None)]
        a.feed(s,t,first,{'level':27,'exp':1009},1)
        a.feed(s,t,first+[('exp',7),('bonus',2)],None,20)
        self.assertEqual(s['exp'],18)
    def test_level_boundary_with_late_bonus(self):
        s,a,t=self.setup_account();a=TrainingAccountant()
        a.feed(s,t,[],{'level':27,'exp':63660},0)
        a.feed(s,t,[('exp',7),('bonus',None)],{'level':28,'exp':3},1)
        a.feed(s,t,[('exp',7),('bonus',2)],None,2)
        a.feed(s,t,[('exp',7),('bonus',2)],None,20)
        self.assertEqual(s['exp'],9)
    def test_missing_old_bonus_does_not_consume_next_complete_reward(self):
        s,a,t=self.setup_account();first=[('exp',7),('bonus',None)]
        a.feed(s,t,first,{'level':27,'exp':1009},1)
        events=first+[('exp',7),('bonus',2)]
        a.feed(s,t,events,None,2);a.feed(s,t,events,None,20)
        self.assertEqual(s['exp'],18)
    def test_late_refinement_alongside_new_base_is_matched(self):
        s,a,t=self.setup_account()
        a.feed(s,t,[('exp',7),('bonus',None)],{'level':27,'exp':1009},1)
        events=[('exp',7),('bonus',2),('exp',7)]
        a.feed(s,t,events,None,2);a.feed(s,t,events,None,20)
        self.assertEqual(s['exp'],16)
        a.feed(s,t,events+[('bonus',2)],None,21)
        self.assertEqual(s['exp'],18)
    def test_death_does_not_recredit_previously_covered_late_bonus(self):
        s,a,t=self.setup_account()
        a.feed(s,t,[],{'level':27,'exp':1000},0)
        a.feed(s,t,[('exp',7),('bonus',None)],{'level':27,'exp':1009},1)
        a.feed(s,t,[('exp',7),('bonus',None)],{'level':27,'exp':900},2)
        a.feed(s,t,[('exp',7),('bonus',2)],None,3)
        a.feed(s,t,[('exp',7),('bonus',2)],None,20)
        self.assertEqual(s['exp'],-100)
        # The next genuinely new reward must still count in partial-log mode.
        events=[('exp',7),('bonus',2),('exp',7),('bonus',2)]
        a.feed(s,t,events,None,21)
        self.assertEqual(s['exp'],-91)
    def test_next_event_trailing_bonus_is_not_old_covered_bonus(self):
        s,a,t=self.setup_account()
        a.feed(s,t,[('exp',7),('bonus',None)],{'level':27,'exp':1009},1)
        a.feed(s,t,[('exp',7),('bonus',None),('exp',7)],None,2)
        events=[('exp',7),('bonus',None),('exp',7),('bonus',2)]
        a.feed(s,t,events,None,3);a.feed(s,t,events,None,20)
        self.assertEqual(s['exp'],18)
        a.feed(s,t,events,{'level':27,'exp':1018},21)
        self.assertEqual(s['exp'],18)
    def test_old_refined_bonus_still_excluded_while_new_base_pending(self):
        s,a,t=self.setup_account()
        a.feed(s,t,[('exp',7),('bonus',None)],{'level':27,'exp':1009},1)
        a.feed(s,t,[('exp',7),('bonus',None),('exp',7)],None,2)
        events=[('exp',7),('bonus',2),('exp',7)]
        a.feed(s,t,events,None,3);a.feed(s,t,events,None,20)
        self.assertEqual(s['exp'],16)
        a.feed(s,t,events+[('bonus',2)],None,21)
        self.assertEqual(s['exp'],18)
    def test_old_inserted_bonus_does_not_become_next_event_bonus(self):
        s,a,t=self.setup_account()
        a.feed(s,t,[('exp',7)],{'level':27,'exp':1009},1)
        a.feed(s,t,[('exp',7),('exp',7)],None,2)
        events=[('exp',7),('bonus',2),('exp',7)]
        a.feed(s,t,events,None,3);a.feed(s,t,events,None,20)
        self.assertEqual(s['exp'],16)
        a.feed(s,t,events+[('bonus',2)],None,21)
        self.assertEqual(s['exp'],18)
    def test_seeded_notice_and_hud_delays_cross_level_boundary(self):
        import leveling
        for seed in range(100):
            rng=random.Random(seed);s,a,t=self.setup_account();a=TrainingAccountant()
            start=63650;events=[];hud=0;schedule=[]
            for index in range(12):
                base=4+index*4
                schedule.append((base,base+rng.randrange(3),base+rng.randrange(3)))
            cutoff=schedule[-1][2]
            a.feed(s,t,[],{'level':27,'exp':start},0)
            for now in range(1,cutoff+21):
                for index,(base,bonus_at,hud_at) in enumerate(schedule):
                    if now==base:events.extend([('exp',7),('bonus',None)])
                    if now==bonus_at:events[index*2+1]=('bonus',2)
                    if now==hud_at:hud+=9
                reading=None
                if now<=cutoff:
                    lv=27;n=start+hud
                    while n>=leveling.exp_to_next(lv):n-=leveling.exp_to_next(lv);lv+=1
                    reading={'level':lv,'exp':n}
                a.feed(s,t,list(events[-12:]),reading,now)
            self.assertEqual(s['exp'],108,msg=f'seed={seed}')

if __name__=='__main__':unittest.main()

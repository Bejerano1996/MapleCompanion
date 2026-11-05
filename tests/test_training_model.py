import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from training_model import *
class TrainingTests(unittest.TestCase):
 def test_reading_far_from_saved_level(self):
  r=character_reading(['LV. 27','EXP. 31,833 [50.00%]'],level_hint=2);self.assertEqual((r['level'],r['exp']),(27,31833))
 def test_no_guess_from_percent(self):self.assertIsNone(character_reading(['EXP 50.00%']))
 def test_conflicting_hud(self):self.assertIsNone(character_reading(['LV. 2','EXP. 31,833 [50.00%]']))
 def test_unsupported_explicit_hud_level_never_falls_back_to_another_level(self):
  for level in (0,100,200,999):
   with self.subTest(level=level):self.assertIsNone(character_reading([f'LV. {level}','EXP. 31,833 [50.00%]']))
 def test_supported_level_can_still_be_inferred_without_hud(self):
  self.assertEqual(character_reading(['EXP. 31,833 [50.00%]'])['level'],27)
 def test_ledger_not_double_log(self):
  x=ExpLedger();self.assertIsNone(x.observe({'level':27,'exp':1000},session_exp=50,now=0))
  self.assertEqual(x.observe({'level':27,'exp':1100},session_exp=150,now=5),150)
 def test_level_up(self):
  x=ExpLedger();x.observe({'level':27,'exp':63600},0,0);self.assertEqual(x.observe({'level':28,'exp':34},0,5),100)
 def test_multiple_level_quest_gain_requires_confirmation(self):
  x=ExpLedger();x.observe({'level':10,'exp':100},0,0)
  self.assertIsNone(x.observe({'level':13,'exp':200},0,5))
  expected=sum(leveling.exp_to_next(i) for i in (10,11,12))+100
  self.assertEqual(x.observe({'level':13,'exp':200},0,10),expected)
 def test_lower_level_rebaselines_without_giant_loss(self):
  x=ExpLedger();x.observe({'level':27,'exp':100},20,0)
  self.assertIsNone(x.observe({'level':25,'exp':200},20,5))
  self.assertEqual(x.observe({'level':25,'exp':200},20,10),20)
 def test_jump_confirmation_requires_consecutive_samples(self):
  for target in (25,30):
   with self.subTest(target=target):
    x=ExpLedger();x.observe({'level':27,'exp':1000},0,0)
    self.assertIsNone(x.observe({'level':target,'exp':100},0,1))
    self.assertEqual(x.observe({'level':27,'exp':1009},0,2),9)
    self.assertIsNone(x.observe({'level':target,'exp':100},9,3))
    self.assertEqual(x.last['level'],27)
 def test_pending_jump_expires_before_later_confirmation(self):
  for target in (25,30):
   with self.subTest(target=target):
    x=ExpLedger();x.observe({'level':27,'exp':1000},0,0)
    self.assertIsNone(x.observe({'level':target,'exp':100},0,1))
    self.assertIsNone(x.observe({'level':target,'exp':100},0,1000))
    self.assertEqual(x.last['level'],27)
    self.assertIsNotNone(x.observe({'level':target,'exp':100},0,1001))
 def test_pending_jump_confirmation_freshness_boundary(self):
  x=ExpLedger();x.observe({'level':27,'exp':1000},0,0)
  x.observe({'level':30,'exp':100},0,1)
  self.assertIsNotNone(x.observe({'level':30,'exp':100},0,16))
 def test_death_is_net_loss(self):
  x=ExpLedger();x.observe({'level':27,'exp':1000},0,0);self.assertEqual(x.observe({'level':27,'exp':900},0,5),-100)
 def test_round_up_kills(self):
  r=training_forecast({'level':27,'exp':63600},{'name':'Evil Eye','exp':50});self.assertEqual(r['kills'],2)
 def test_decimal_personal_yield_exact_boundary(self):
  r=training_forecast({'level':5,'exp':114},{'name':'probe','exp':1},personal_gain=1.4)
  self.assertEqual(r['kills'],15)
 def test_decimal_personal_yield_rounds_up_only_remainder(self):
  r=training_forecast({'level':5,'exp':113},{'name':'probe','exp':1},personal_gain=1.4)
  self.assertEqual(r['kills'],16)
 def test_party_total_tracks_only_own_level_change(self):
  self.assertEqual(adjusted_party_total(54,27,28),55)
  self.assertEqual(adjusted_party_total(None,27,28),None)
  result=training_forecast({'level':28,'exp':0},{'name':'Evil Eye','exp':50},party=2,party_levels=adjusted_party_total(54,27,28))
  self.assertEqual(result['gain'],29)
 def test_party_split_not_blanket_multiplier(self):
  r=training_forecast({'level':27,'exp':63600},{'name':'Evil Eye','exp':50},party=2,hits='all');self.assertEqual(r['gain'],29);self.assertEqual(r['kills'],3)
 def test_unknowns(self):
  self.assertFalse(training_forecast(None,{'exp':50})['available']);self.assertFalse(training_forecast({'level':100,'exp':0},{'exp':50})['available']);self.assertFalse(training_forecast({'level':27,'exp':0},{'exp':float('nan')})['available'])
class AccountingTests(unittest.TestCase):
 def session(self):return dict(id='test',running_since=1,auto_rewards=True,exp=0,mesos=0,kills=0,cost=0)
 def test_authoritative_bar_recovers_unread_bonus(self):
  from training_accounting import TrainingAccountant
  from session_rewards import session_token
  s=self.session();a=TrainingAccountant();t=session_token(s)
  a.feed(s,t,[],{'level':27,'exp':1000},0)
  a.feed(s,t,[('exp',7)],{'level':27,'exp':1009},5)
  self.assertEqual(s['exp'],9);self.assertEqual(s['party_exp'],0)
 def test_no_reward_log_needed_for_bar(self):
  from training_accounting import TrainingAccountant
  from session_rewards import session_token
  s=self.session();a=TrainingAccountant();t=session_token(s)
  a.feed(s,t,None,{'level':27,'exp':1000},0);a.feed(s,t,None,{'level':27,'exp':1100},5)
  self.assertEqual(s['exp'],100)
 def test_stale_bar_fallback(self):
  from training_accounting import TrainingAccountant
  from session_rewards import session_token
  s=self.session();a=TrainingAccountant();t=session_token(s)
  a.feed(s,t,[],{'level':27,'exp':1000},0);a.feed(s,t,[],{'level':27,'exp':1000},5)
  a.feed(s,t,[('exp',7),('bonus',2),('mesos',10)],None,25)
  a.feed(s,t,[('exp',7),('bonus',2),('mesos',10)],None,26)
  self.assertEqual((s['exp'],s['mesos']),(9,10));self.assertIn('partial',s['exp_source'])
  a.feed(s,t,[('exp',7),('bonus',2),('mesos',10)],{'level':27,'exp':1009},30)
  self.assertEqual(s['exp'],9)
 def test_stale_token_cannot_modify_session(self):
  from training_accounting import TrainingAccountant
  s=self.session();before=dict(s);TrainingAccountant().feed(s,('other',1,True),[('mesos',10)],{'level':27,'exp':10},0)
  self.assertEqual(s,before)

if __name__=='__main__':unittest.main()

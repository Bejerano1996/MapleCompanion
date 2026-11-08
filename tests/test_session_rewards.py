import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from session_rewards import RewardTracker,reward_event,session_token,apply_rewards
class RewardsTests(unittest.TestCase):
 def test_spatial_scroll_counts_equal_pickup_again(self):
  from session_reader import RewardRead
  def rows(events):return RewardRead(events,False,range(len(events)),[(20*i,12) for i in range(len(events))])
  t=RewardTracker(confirm_money=2)
  t.feed(rows([('exp',7),('bonus',2),('mesos',10)]))
  result=t.feed(rows([('bonus',2),('mesos',10),('mesos',10)]))
  self.assertEqual(result['mesos'],10)
  self.assertEqual(t.feed(rows([('bonus',2),('mesos',10),('mesos',10)]))['mesos'],0)
 def test_spatial_alignment_respects_scroll_offset(self):
  old=[('exp',7),('bonus',2),('mesos',10)]
  new=[('bonus',2),('mesos',10),('mesos',18)]
  positions=[(0,12),(20,12),(40,12)]
  self.assertEqual(RewardTracker._align(old,new,positions,positions),[(1,0),(2,1)])
 def test_partial_equal_rows_do_not_invent_scroll_from_one_amount(self):
  positions=[(0,12),(20,12),(40,12)]
  old=[('mesos',None),('mesos',23),('mesos',None)]
  new=[('mesos',None),('mesos',None),('mesos',23)]
  self.assertEqual(RewardTracker._align(old,new,positions,positions),[(0,0),(1,1),(2,2)])
 def test_trailing_bonus_provenance_does_not_change_public_delta(self):
  t=RewardTracker();t.feed([]);t.feed([('exp',7),('bonus',None)])
  t.feed([('exp',7),('bonus',None),('exp',7)])
  events=[('exp',7),('bonus',None),('exp',7),('bonus',2)]
  self.assertEqual(t.feed(events),dict(exp=2,kills=0,mesos=0,party_exp=2))
  self.assertEqual(t.trailing_party_exp,2);self.assertEqual(t.refined_party_exp,0)
  t.feed(events);self.assertEqual(t.trailing_party_exp,0)
  events[1]=('bonus',2);t.feed(events)
  self.assertEqual(t.trailing_party_exp,0);self.assertEqual(t.refined_party_exp,2)
 def test_periodic_partial_rows_do_not_prove_movement_with_two_amounts(self):
  positions=[(20*i,12) for i in range(4)]
  old=[('mesos',10),('mesos',20),('mesos',None),('mesos',None)]
  new=[('mesos',None),('mesos',None),('mesos',10),('mesos',20)]
  self.assertEqual(RewardTracker._align(old,new,positions,positions),[(0,0),(1,1),(2,2),(3,3)])
 def test_stationary_periodic_baseline_never_becomes_new_pickup(self):
  from session_reader import RewardRead
  import random
  rng=random.Random(3);t=RewardTracker(confirm_money=2);total=0;values=[10,20]*3;positions=[(20*i,12) for i in range(6)]
  for _ in range(20):
   events=[('mesos',v if rng.random()<.45 else None) for v in values]
   total+=t.feed(RewardRead(events,False,(),positions))['mesos']
  self.assertEqual(total,0)
 def test_clear_money_does_not_require_second_frame(self):
  from session_reader import RewardRead
  t=RewardTracker(confirm_money=2);t.feed([])
  self.assertEqual(t.feed(RewardRead([('mesos',22)],False,[0]))['mesos'],22)
  self.assertEqual(t.feed(RewardRead([('mesos',22)],False,[0]))['mesos'],0)
 def test_partial_empty_does_not_reset_old_notices(self):
  from session_reader import RewardRead
  t=RewardTracker();t.feed([('mesos',10)])
  for _ in range(8):t.feed(RewardRead())
  self.assertEqual(t.feed([('mesos',10)])['mesos'],0)
 def test_new_single_notice_replaces_previous_amount(self):
  t=RewardTracker(confirm_money=2);t.feed([('mesos',10)])
  self.assertEqual(t.feed([('mesos',18)])['mesos'],0)
  self.assertEqual(t.feed([('mesos',18)])['mesos'],18)
  self.assertEqual(t.feed([('mesos',18)])['mesos'],0)
 def test_parser(self):
  for text,event in [('You received EXP (+7)',('exp',7)),('Bonus EXP for PARTY (+2)',('bonus',2)),('You have gained mesos (+10)',('mesos',10)),('have qained mesos f+7)',('mesos',7))]:self.assertEqual(reward_event(text),event)
  for text in ('Salad 220 mesos','Quest EXP 500','You lost mesos (-7)','You received EXP (+100000001)'):self.assertIsNone(reward_event(text))
 def test_malformed_thousands_groups_are_not_concrete_rewards(self):
  for amount in ('1,2','1,,000','1,234,','12,34','1234,567'):
   for prefix in ('You have gained mesos','You received EXP','Bonus EXP for PARTY'):
    with self.subTest(amount=amount,prefix=prefix):self.assertIsNone(reward_event(prefix+' (+'+amount+')'))
 def test_valid_grouped_and_space_split_amounts_remain_supported(self):
  for amount,value in [('1,234',1234),('12,345,678',12345678),('1234',1234),('1 234',1234),('1, 234',1234)]:
   self.assertEqual(reward_event('You have gained mesos (+'+amount+')'),('mesos',value))
 def test_merged_reward_messages_are_not_one_relabelled_amount(self):
  for text in ('You received EXP (+7) Bonus EXP for PARTY (+2)',
               'You received EXP (+7) You have gained mesos (+10)',
               'You have gained mesos (+10) You have gained mesos (+20)',
               'You received EXP (+7) Bonus EXP for PARTY (+?)',
               'You received EXP (+?) You have gained mesos (+10)'):
   with self.subTest(text=text):self.assertIsNone(reward_event(text))
 def test_baseline_and_duplicate(self):
  t=RewardTracker();a=[('mesos',10)];self.assertFalse(any(t.feed(a).values()));self.assertFalse(any(t.feed(a).values()))
  b=a+[('exp',7),('bonus',2),('mesos',7)]
  self.assertEqual(t.feed(b),dict(exp=9,kills=1,mesos=7,party_exp=2));self.assertFalse(any(t.feed(b).values()))
 def test_repeated_equal_rewards(self):
  t=RewardTracker();t.feed([('mesos',10)]);self.assertEqual(t.feed([('mesos',10),('mesos',10)])['mesos'],10)
 def test_scroll(self):
  t=RewardTracker();t.feed([('exp',5),('mesos',10)]);self.assertEqual(t.feed([('mesos',10),('exp',7)])['exp'],7)
 def test_loss_of_continuity(self):
  t=RewardTracker();t.feed([('exp',5)]);self.assertFalse(any(t.feed([('mesos',999)]).values()))
 def test_blank_and_unavailable(self):
  t=RewardTracker();t.feed([('exp',5)]);t.feed([]);t.feed([]);t.feed([]);t.feed([]);self.assertEqual(t.feed([('exp',5)])['exp'],5)
  t.feed(None);self.assertFalse(any(t.feed([('exp',5)]).values()))
 def test_pause_and_archive(self):
  s=dict(id='a',running_since=1,exp=2,mesos=3,kills=0,cost=10);token=session_token(s)
  self.assertTrue(apply_rewards(s,token,dict(exp=7,mesos=10,kills=1)));self.assertEqual(s['cost'],10)
  s['running_since']=None;self.assertFalse(apply_rewards(s,token,dict(exp=7)));s.update(id='b',running_since=1);self.assertFalse(apply_rewards(s,token,dict(exp=7)))
 def test_money_needs_two_matching_reads(self):
  t=RewardTracker(confirm_money=2);t.feed([])
  self.assertEqual(t.feed([('mesos',10)])['mesos'],0)
  self.assertEqual(t.feed([('mesos',10)])['mesos'],10)
  self.assertEqual(t.feed([('mesos',10)])['mesos'],0)
 def test_fading_amount_does_not_add_new_money(self):
  t=RewardTracker(confirm_money=2);t.feed([]);t.feed([('mesos',10)]);t.feed([('mesos',10)])
  self.assertEqual(t.feed([('mesos',70)])['mesos'],0)
  self.assertEqual(t.feed([('mesos',10)])['mesos'],0)
 def test_wrong_first_amount_can_be_refined_before_credit(self):
  t=RewardTracker(confirm_money=2);t.feed([]);t.feed([('mesos',70)])
  self.assertEqual(t.feed([('mesos',10)])['mesos'],0)
  self.assertEqual(t.feed([('mesos',10)])['mesos'],10)
 def test_initial_empty_does_not_drop_pickup(self):
  t=RewardTracker();t.feed([]);self.assertEqual(t.feed([('mesos',10)])['mesos'],10)
 def test_late_amount_read(self):
  t=RewardTracker();t.feed([]);t.feed([]);t.feed([]);t.feed([])
  t.feed([('mesos',None)])
  self.assertEqual(t.feed([('mesos',10)])['mesos'],10)
  self.assertEqual(t.feed([('mesos',10)])['mesos'],0)
 def test_recovered_old_amount_excluded(self):
  t=RewardTracker();t.feed([('mesos',None)]);self.assertEqual(t.feed([('mesos',10)])['mesos'],0)
 def test_party_refinement_no_duplicate_base(self):
  t=RewardTracker();t.feed([('mesos',1)])
  t.feed([('mesos',1),('exp',7),('bonus',None),('exp',7)])
  delta=t.feed([('mesos',1),('exp',7),('bonus',2),('exp',7)])
  self.assertEqual(delta,dict(exp=2,kills=0,mesos=0,party_exp=2))
 def test_brief_ocr_dropout_not_new_money(self):
  t=RewardTracker();t.feed([('mesos',10)]);t.feed([]);t.feed([])
  self.assertEqual(t.feed([('mesos',10)])['mesos'],0)
 def test_party_ocr_formats(self):
  for text in ('BorusEXPforPARTY（+2）','Bonus EXPfor PARTY (+2','Bonus EXP for PARTY (+2)'):
   self.assertEqual(reward_event(text),('bonus',2))
  self.assertIsNone(reward_event('Bonus EXP for PARTY (+?'))
 def test_manual_mode(self):
  s=dict(id='a',running_since=1,auto_rewards=False);self.assertFalse(apply_rewards(s,session_token(s),dict(exp=7)))
if __name__=='__main__':unittest.main()

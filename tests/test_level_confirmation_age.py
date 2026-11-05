from pathlib import Path
import sys,unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app,training_ui,leveling
class LevelConfirmationAgeTests(unittest.TestCase):
 def run_gap(self,gap):
  accepted=[];a=SimpleNamespace(_reads={},training_accept_character=lambda r:accepted.append(r))
  confirm=lambda *args:app.App._confirmed(a,*args)
  texts=['LV.28','EXP 1000',f'{leveling.percent(1000,28):.2f}%']
  with patch.object(training_ui.time,'monotonic',return_value=100.):training_ui.training_on_exp_bar(a,texts,confirm)
  self.assertFalse(accepted)
  with patch.object(training_ui.time,'monotonic',return_value=100.+gap):training_ui.training_on_exp_bar(a,texts,confirm)
  return a,accepted,confirm,texts
 def test_normal_and_boundary_intervals_confirm(self):
  for gap in (0.,6.,15.):
   with self.subTest(gap=gap):self.assertEqual(len(self.run_gap(gap)[1]),1)
 def test_stale_confirmation_requires_two_new_reads(self):
  for gap in (15.001,60.,3600.):
   with self.subTest(gap=gap):
    a,accepted,confirm,texts=self.run_gap(gap);self.assertFalse(accepted)
    with patch.object(training_ui.time,'monotonic',return_value=101.+gap):training_ui.training_on_exp_bar(a,texts,confirm)
    self.assertEqual(len(accepted),1)
 def test_partial_hud_does_not_extend_confirmation_freshness(self):
  a,accepted,confirm,texts=self.run_gap(6.)
  self.assertEqual(len(accepted),1)
  last=a._training_level_confirmation_at
  with patch.object(training_ui.time,'monotonic',return_value=120.):training_ui.training_on_exp_bar(a,['EXP 1000'],confirm)
  self.assertEqual(a._training_level_confirmation_at,last)
  with patch.object(training_ui.time,'monotonic',return_value=122.):training_ui.training_on_exp_bar(a,texts,confirm)
  self.assertEqual(len(accepted),1)
  with patch.object(training_ui.time,'monotonic',return_value=123.):training_ui.training_on_exp_bar(a,texts,confirm)
  self.assertEqual(len(accepted),2)
if __name__=='__main__':unittest.main()

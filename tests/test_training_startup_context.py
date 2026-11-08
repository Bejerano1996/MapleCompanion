import sys,unittest,types,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import training_ui
class StartupTests(unittest.TestCase):
 def app(self,automatic=True):
  a=types.SimpleNamespace(state=dict(training_auto_context=automatic,training_target='23',map='a',party=1,character_exp={'level':27,'exp':1000},character_exp_at=time.time(),training_personal_gain=None),db=types.SimpleNamespace(monsters={23:dict(id=23,name='probe',exp=50)},map_data={'a':{'monsters':[{'id':'23','count':10}]}}))
  for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total','training_forecast_now','training_observe_yield'):
   setattr(a,name,types.MethodType(getattr(training_ui,name),a))
  return a
 def test_automatic_startup_never_uses_saved_manual_target(self):
  a=self.app();self.assertIsNone(a.training_target());self.assertFalse(a.training_forecast_now()['available'])
  self.assertFalse(a.training_observe_yield(dict(exp=9,kills=1),{'level':27,'exp':1000},{'level':27,'exp':1009}))
 def test_explicit_none_or_empty_context_is_still_unknown(self):
  for context in (None,{}):
   a=self.app();a._training_context=context
   self.assertIsNone(a.training_target());self.assertFalse(a.training_forecast_now()['available'])
 def test_fresh_confirmed_context_enables_observed_target(self):
  a=self.app();a.state['training_target']='999';now=time.time()
  a._training_context=dict(map='a',map_readable=True,map_at=now,mobs=[23],mobs_at=now,party_visible=2,party_readable=True,party_at=now)
  self.assertEqual(a.training_target()['id'],23);self.assertTrue(a.training_forecast_now()['available'])
 def test_manual_override_remains_available_without_context(self):
  a=self.app(False);self.assertEqual(a.training_target()['id'],23);self.assertTrue(a.training_forecast_now()['available'])
if __name__=='__main__':unittest.main()

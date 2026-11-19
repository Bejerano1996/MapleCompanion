from pathlib import Path
import sys,types,unittest,copy,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import training_context
class ContextGenerationTests(unittest.TestCase):
 def run_case(self,restart):
  pending=[];renders=[]
  root=types.SimpleNamespace(winfo_children=lambda:[],winfo_viewable=lambda:False)
  a=types.SimpleNamespace(root=root,state={'utility_session':{'id':'same','running_since':1,'auto_rewards':True}},db=types.SimpleNamespace(maps={'a':{}},monsters={}),run_bg=lambda work,loaded,on_error:pending.append(loaded),render_levelup=lambda:renders.append(1))
  training_context.context_poll(a);before=copy.deepcopy(a._training_context)
  if restart:a._context_generation=1
  pending.pop()({'game':True,'map':'a','mobs':[23],'party_visible':2,'captured_at':time.time()})
  self.assertFalse(a._context_busy)
  return a,before,renders
 def test_generation_change_rejects_old_context(self):
  a,before,renders=self.run_case(True)
  self.assertEqual(a._training_context,before);self.assertFalse(renders)
  self.assertNotIn('observed_monsters',a.state['utility_session'])
 def test_same_generation_keeps_valid_context(self):
  a,before,renders=self.run_case(False)
  self.assertEqual(a._training_context['mobs'],[23]);self.assertEqual(len(renders),1)
  self.assertIn('23',a.state['utility_session']['observed_monsters'])
if __name__=='__main__':unittest.main()

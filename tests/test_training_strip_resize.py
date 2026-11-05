import sys,unittest,types,tkinter as tk
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from training_ui import training_render_levelup
class StripTests(unittest.TestCase):
 def test_width_change_updates_wrap_without_repeated_rebuild(self):
  root=tk.Tk();root.withdraw()
  try:
   width=340;a=types.SimpleNamespace(state={'character_exp':{'level':27,'exp':1000,'percent':1.5}},_lvl_spec=None,lvl_strip=tk.Frame(root),panel_width=lambda:width,training_forecast_now=lambda:{'available':True,'kills':5},training_forecast_text=lambda:'Approximate remaining kills with a long monster name',companion_exp_details=lambda:None)
   training_render_levelup(a);self.assertEqual(int(a.lvl_strip._training_nodes[1].cget('wraplength')),305)
   original=tuple(str(w) for w in a.lvl_strip.winfo_children())
   width=520;training_render_levelup(a)
   self.assertEqual(original,tuple(str(w) for w in a.lvl_strip.winfo_children()))
   self.assertEqual(int(a.lvl_strip._training_nodes[1].cget('wraplength')),485)
   nodes=tuple(str(w) for w in a.lvl_strip.winfo_children())
   a.state['character_exp']['exp']=1009;training_render_levelup(a)
   self.assertEqual(nodes,tuple(str(w) for w in a.lvl_strip.winfo_children()))
   width=280;training_render_levelup(a)
   self.assertEqual(int(a.lvl_strip._training_nodes[1].cget('wraplength')),245)
  finally:root.destroy()
if __name__=='__main__':unittest.main()

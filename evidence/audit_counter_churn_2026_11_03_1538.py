from pathlib import Path
import sys,types,tkinter as tk,json,hashlib,time
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
import training_ui,widgets
root=tk.Tk();root.withdraw();errors=[];root.report_callback_exception=lambda k,e,t:errors.append(str(e))
width=[340];text=[''];forecast=[{}]
a=types.SimpleNamespace(state={'character_exp':{'level':27,'exp':1000,'percent':1.5}},_lvl_spec=None,lvl_strip=tk.Frame(root,bg=widgets.C['card']),panel_width=lambda:width[0],training_forecast_now=lambda:forecast[0],training_forecast_text=lambda:text[0],companion_exp_details=lambda:None)
from companion_widgets import ui_walk_widgets
max_widgets=0;reused=0;rebuilds=0;oldnodes=None;oldscale=None;start=time.perf_counter();samples=[]
for i in range(1000):
 widgets.text_scale=(1.,1.15,1.3)[(i//50)%3];width[0]=(260,280,340,460,580)[i%5]
 a.state['character_exp'].update(exp=1000+i,percent=1.5+i*.001)
 forecast[0]={'available':i%3!=0,'kills':i+1,'party':i%6+1}
 text[0]=('Read the EXP bar or set level and current EXP' if i%3==0 else f'Approximate {i+1:,} Evil Eye / Cold Eye remaining with party {i%6+1}')
 training_ui.training_render_levelup(a);root.update_idletasks()
 nodes=tuple(str(w) for w in a.lvl_strip.winfo_children())
 if oldscale==widgets.text_scale:
  assert nodes==oldnodes
  reused+=1
 elif oldnodes is not None:rebuilds+=1
 oldnodes=nodes;oldscale=widgets.text_scale
 count=len(list(ui_walk_widgets(a.lvl_strip)));max_widgets=max(max_widgets,count)
 assert count<=7,count
 assert int(a.lvl_strip._training_nodes[1].cget('wraplength'))==max(200,width[0]-35)
 assert a.lvl_strip._training_nodes[1].cget('text')==text[0]
 if i%50==49:samples.append(len(root.tk.call('info','commands')))
assert not errors,errors
assert max(samples)-min(samples)<=10,samples
report=dict(ok=True,updates=1000,same_font_widget_reuses=reused,font_rebuilds=rebuilds,max_widgets=max_widgets,tcl_command_counts=samples,elapsed_seconds=round(time.perf_counter()-start,3),tk_errors=errors,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Isolated actual native compact counter rendering with synthetic EXP/party/text, width/font churn; no live app/game')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));root.destroy()

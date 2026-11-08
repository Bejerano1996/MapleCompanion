"""Windows CI packaging and optional publication for a new source version."""
import argparse,json,os,re,subprocess,zipfile
from pathlib import Path
from github_release_api import GitHub,sha256
PRIVATE={'.git','.build','dist','cache','__pycache__','.venv','_local_state'}
NAMES={'state.json','logic_state.json','flicker_state.json','show.request','.env','credentials.json'}
def version(root):
 text=(root/'companion_integration.py').read_text(encoding='utf-8-sig')
 value=re.search(r"core\['VERSION'\]\s*=\s*['\"]([^'\"]+)",text)[1]
 return value.removesuffix('.0-companion') if value.endswith('.0-companion') else value.removesuffix('-companion')
def archive(origin,target,label):
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
  for path in sorted(origin.rglob('*')):
   rel=path.relative_to(origin)
   if not path.is_file() or any(p.lower() in PRIVATE for p in rel.parts) or path.name.lower() in NAMES or path.name.lower().startswith('.env') or path.suffix in ('.pyc','.log','.key'):continue
   z.write(path,Path(label)/rel)
 with zipfile.ZipFile(target) as z:
  if z.testzip() is not None:raise RuntimeError('Corrupt generated ZIP')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--publish',action='store_true');parser.add_argument('--plan',action='store_true');a=parser.parse_args()
 root=Path(__file__).resolve().parents[1];v=version(root);tag='umbrale-v'+v
 tags=subprocess.check_output(['git','tag','--list',tag],cwd=root,text=True).splitlines();exists=tag in tags
 if a.plan:
  with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('version='+v+'\nbuild='+str(not exists or os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch').lower()+'\n')
  return
 folder=root/'release-artifacts';folder.mkdir(exist_ok=True)
 program=folder/f'Umbrale Companion {v}.zip';source=folder/f'Umbrale Companion {v} Source.zip'
 archive(root/'dist/Umbrale Companion',program,f'Umbrale Companion {v}')
 # Output folder must never recursively include itself in source archive.
 target_source=root/'release-artifacts';PRIVATE.add('release-artifacts')
 archive(root,source,f'Umbrale Companion {v} Source')
 assets=[{'name':p.name,'sha256':sha256(p),'size':p.stat().st_size} for p in (program,source)]
 sums=folder/'SHA256SUMS.txt';sums.write_text(''.join(x['sha256']+'  '+x['name']+'\n' for x in assets))
 report=folder/'release-manifest.json';report.write_text(json.dumps({'version':v,'tag':tag,'commit':os.environ.get('GITHUB_SHA'),'assets':assets,'validation':'focused regression checks and ZIP CRC'},indent=2))
 if a.publish:
  if exists:raise RuntimeError('Version already exists; never overwrite historical releases')
  api=GitHub('Bejerano1996/MapleCompanion');release=api.release(tag,os.environ['GITHUB_SHA'],'Umbrale Companion '+v,'Windows build and source for this verified version. Saves and caches are excluded. See SHA256SUMS.txt.',latest=True)
  for p in (program,source,sums,report):api.asset(release,p,sha256(p))
  print(release['html_url'])
 else:print('Verified build artifacts only; no release published')
if __name__=='__main__':main()

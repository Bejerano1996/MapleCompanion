"""Publish a verified version to Git and GitHub Releases; no character saves are copied."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,zipfile
from github_release_api import GitHub,sha256
EXCLUDED={'.git','cache','__pycache__','.build','.venv','dist','_local_state','build','backups','backup'}
PRIVATE={'state.json','logic_state.json','flicker_state.json','show.request','.env','credentials.json'}
PRESERVED={'.github','tools','releases','release-index.json','RELEASES.md','AGENTS.md'}
def allowed(path):
 return not any(p.lower() in EXCLUDED for p in path.parts) and path.name.lower() not in PRIVATE and not path.name.lower().startswith('.env') and path.suffix.lower() not in {'.pyc','.log','.key'} and not (path.name.lower().startswith('state') and path.suffix.lower()=='.json')
def verify_archive(path):
 with zipfile.ZipFile(path) as z:
  if z.testzip() is not None:raise ValueError('Corrupt archive')
  for entry in z.infolist():
   rel=Path(entry.filename)
   if rel.is_absolute() or '..' in rel.parts or not allowed(rel):raise ValueError('Unsafe/private archive entry: '+entry.filename)
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True,stderr=subprocess.PIPE).strip()
def stage_source(repo,source):
 if source==repo:return
 if source.is_relative_to(repo) or repo.is_relative_to(source):raise ValueError("Source and release checkout must not be nested")
 for tracked in git(repo,'ls-files').splitlines():
  rel=Path(tracked)
  if rel.parts[0] in PRESERVED:continue
  path=repo/rel
  if path.is_file():path.unlink()
 for path in source.rglob('*'):
  rel=path.relative_to(source)
  if path.is_file() and allowed(rel) and rel.parts[0] not in PRESERVED:
   target=repo/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)

def main():
 p=argparse.ArgumentParser();p.add_argument('--version',required=True);p.add_argument('--source-dir',type=Path,required=True);p.add_argument('--repo-dir',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--program-zip',type=Path,required=True);p.add_argument('--source-zip',type=Path,required=True);p.add_argument('--release-manifest',type=Path,required=True)
 a=p.parse_args();repo=a.repo_dir.resolve();source=a.source_dir.resolve()
 if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?',a.version):raise ValueError('Invalid version')
 tag='umbrale-v'+a.version;repository='Bejerano1996/MapleCompanion'
 if git(repo,'branch','--show-current')!='main':raise ValueError('Publish from main only')
 from ci_release import version
 if version(source)!=a.version:raise ValueError('Source version does not match release version')
 if git(repo,'remote','get-url','origin').rstrip('/') not in ('https://github.com/'+repository+'.git','https://github.com/'+repository):raise ValueError('Wrong Git remote')
 manifest=json.loads(a.release_manifest.read_text())
 if not manifest.get('frozen_checks'):raise ValueError('Packaged validation must pass before publication')
 assets=[]
 for archive in (a.program_zip,a.source_zip):
  verify_archive(archive)
  digest=sha256(archive)
  if manifest.get('archives',{}).get(archive.name)!=digest:raise ValueError('Archive hash differs from validated manifest')
  assets.append({'name':archive.name,'sha256':digest,'size':archive.stat().st_size})
 if git(repo,'status','--porcelain'):raise ValueError('Release clone has uncommitted changes')
 if tag in git(repo,'tag','--list',tag).splitlines():
  saved=repo/'releases'/(tag+'.json')
  if not saved.is_file() or json.loads(saved.read_text()).get('assets')!=assets:raise ValueError('Published version differs; never rewrite it')
  commit=git(repo,'rev-parse',tag+'^{commit}')
 else:
  stage_source(repo,source)
  release={'tag':tag,'version':a.version,'family':'umbrale','source_available':True,'assets':assets}
  folder=repo/'releases';folder.mkdir(exist_ok=True)
  (folder/(tag+'.json')).write_text(json.dumps(release,indent=2))
  index_path=repo/'release-index.json';index=json.loads(index_path.read_text());index['latest']=tag;index['versions'].append(release);index_path.write_text(json.dumps(index,indent=2))
  git(repo,'add','-A');git(repo,'commit','-m','Release Umbrale Companion '+a.version);commit=git(repo,'rev-parse','HEAD');git(repo,'tag','-a',tag,'-m','Umbrale Companion '+a.version)
 git(repo,'push','--atomic','origin','main',tag)
 api=GitHub(repository);remote=api.release(tag,commit,'Umbrale Companion '+a.version,'Verified source and Windows program archives. Character saves and caches are excluded. See SHA256SUMS.txt.',latest=True)
 for archive,info in zip((a.program_zip,a.source_zip),assets):api.asset(remote,archive,info['sha256'])
 sums=a.release_manifest.parent/(tag+'-SHA256SUMS.txt');sums.write_text(''.join(x['sha256']+'  '+x['name'].replace(' ','.')+'\n' for x in assets))
 api.asset(remote,sums,sha256(sums));api.asset(remote,a.release_manifest,sha256(a.release_manifest))
 print(remote['html_url'])
if __name__=='__main__':main()

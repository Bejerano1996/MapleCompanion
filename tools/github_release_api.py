"""GitHub Releases transport using the user's configured Git credential helper.
Credentials stay in memory and are never written to logs, manifests or the repository.
"""
import hashlib,http.client,json,os,subprocess,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
class GitHub:
 def __init__(self,repository):
  if repository!='Bejerano1996/MapleCompanion':raise ValueError('Unexpected release destination')
  self.repository=repository
  self.token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
  if not self.token:
   p=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,check=True,env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never'))
   fields=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
   self.token=fields['password']
 def request(self,path,data=None,method=None):
  url=path if path.startswith('https://') else 'https://api.github.com/repos/'+self.repository+path
  if urllib.parse.urlparse(url).hostname!='api.github.com':raise ValueError('Unexpected API host')
  body=json.dumps(data).encode() if data is not None else None
  headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json','User-Agent':'Umbrale-Release-Publisher','X-GitHub-Api-Version':'2022-11-28'}
  if body is not None:headers['Content-Type']='application/json'
  request=urllib.request.Request(url,data=body,headers=headers,method=method)
  for attempt in range(5):
   try:
    with urllib.request.urlopen(request,timeout=90) as r:
     payload=r.read();return json.loads(payload) if payload else None
   except urllib.error.HTTPError as e:
    if e.code not in (429,500,502,503,504) or attempt==4:raise RuntimeError(f'GitHub API {e.code}: {path}') from None
    time.sleep(min(30,2**attempt))
 def release(self,tag,commit,name,body,latest=False):
  try:return self.request('/releases/tags/'+urllib.parse.quote(tag,safe=''))
  except RuntimeError as e:
   if 'API 404:' not in str(e):raise
  return self.request('/releases',{'tag_name':tag,'target_commitish':commit,'name':name,'body':body,'draft':False,'prerelease':False,'make_latest':'true' if latest else 'false'})
 def asset(self,release,path,expected_sha):
  path=Path(path)
  for attempt in range(5):
   assets=self.request(f"/releases/{release['id']}/assets?per_page=100")
   remote_name=path.name.replace(' ','.')
   found=next((a for a in assets if a['name']==remote_name),None)
   if found:
    self.verify(found,path.stat().st_size,expected_sha);return found
   base=release['upload_url'].split('{',1)[0]
   parsed=urllib.parse.urlparse(base)
   if parsed.hostname!='uploads.github.com':raise ValueError('Unexpected upload host')
   connection=http.client.HTTPSConnection(parsed.hostname,timeout=180)
   try:
    target=parsed.path+'?'+urllib.parse.urlencode({'name':remote_name})
    connection.putrequest('POST',target)
    for key,value in {'Authorization':'Bearer '+self.token,'User-Agent':'Umbrale-Release-Publisher','Accept':'application/vnd.github+json','Content-Type':'application/octet-stream','Content-Length':str(path.stat().st_size)}.items():connection.putheader(key,value)
    connection.endheaders()
    with path.open('rb') as f:
     while block:=f.read(1024*1024):connection.send(block)
    response=connection.getresponse();raw=response.read()
    if response.status==201:
     asset=json.loads(raw);self.verify(asset,path.stat().st_size,expected_sha);return asset
    if response.status not in (422,429,500,502,503,504):raise RuntimeError(f'Asset upload HTTP {response.status}: {path.name}')
   except (OSError,http.client.HTTPException):
    if attempt==4:raise
   finally:connection.close()
   time.sleep(2**attempt)
  raise RuntimeError('Asset upload retries exhausted: '+path.name)
 def verify(self,asset,size,sha):
  if asset['size']!=size or asset.get('state')!='uploaded':raise RuntimeError('Remote asset size/state mismatch: '+asset['name'])
  digest=asset.get('digest')
  if digest:
   if digest!='sha256:'+sha:raise RuntimeError('Remote asset hash mismatch: '+asset['name'])
  else:
   request=urllib.request.Request(asset['url'],headers={'Authorization':'Bearer '+self.token,'Accept':'application/octet-stream','User-Agent':'Umbrale-Release-Publisher'})
   h=hashlib.sha256()
   with urllib.request.urlopen(request,timeout=180) as r:
    while block:=r.read(1024*1024):h.update(block)
   if h.hexdigest()!=sha:raise RuntimeError('Downloaded asset hash mismatch: '+asset['name'])
def sha256(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

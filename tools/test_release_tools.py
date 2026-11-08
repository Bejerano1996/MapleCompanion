import hashlib,tempfile,unittest,zipfile
from pathlib import Path
from publish_release import allowed,verify_archive
from github_release_api import GitHub
from ci_release import version
class ReleaseToolsTests(unittest.TestCase):
 def test_private_paths_excluded_required_policy_kept(self):
  for path in ('state.json','cache/a.txt','_local_state/backup.json','.ENV.local','nested/.env.test','nested/credentials.json','temp.pyc'):
   self.assertFalse(allowed(Path(path)),path)
  self.assertTrue(allowed(Path('_internal/codex-rejected-cas.pem')))
  self.assertTrue(allowed(Path('app.py')))
 def test_private_archive_rejected(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as d:
   p=Path(d)/'safe.zip'
   with zipfile.ZipFile(p,'w') as z:z.writestr('Companion/app.py','pass')
   verify_archive(p)
   with zipfile.ZipFile(p,'a') as z:z.writestr('Companion/state.json','{}')
   with self.assertRaises(ValueError):verify_archive(p)
 def test_remote_asset_must_match_hash_and_size(self):
  api=object.__new__(GitHub);digest=hashlib.sha256(b'program').hexdigest()
  asset={'name':'program.zip','size':7,'state':'uploaded','digest':'sha256:'+digest}
  api.verify(asset,7,digest)
  with self.assertRaises(RuntimeError):api.verify(asset,8,digest)
  with self.assertRaises(RuntimeError):api.verify(asset,7,'0'*64)
 def test_application_version_maps_to_existing_tag(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as d:
   root=Path(d);(root/'companion_integration.py').write_text("core['VERSION']='3.37.0-companion'")
   self.assertEqual(version(root),'3.37')
if __name__=='__main__':unittest.main()

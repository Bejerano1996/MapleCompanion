from pathlib import Path
import sys,unittest,queue
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
class MissingGameSyncTests(unittest.TestCase):
 def make_app(self):
  a=object.__new__(app.App);a.syncing=True;a.statuses=[];a.profiles=[];a.scheduled=[]
  a.set_status=lambda *args:a.statuses.append(args);a._companion_profile_refresh=lambda:a.profiles.append(True)
  a.root=type('Root',(),{'after':lambda root,*args:a.scheduled.append(args)})();a.results=queue.Queue()
  return a
 def test_missing_game_clears_busy_and_marks_map_unreadable(self):
  a=self.make_app();a._on_synced(None)
  self.assertFalse(a.syncing);self.assertFalse(a._live_last_result['_minimap_readable'])
  self.assertTrue(a.statuses);self.assertEqual(len(a.profiles),1)
 def test_missing_game_result_does_not_stop_shared_result_pump(self):
  a=self.make_app();received=[];a.results.put((a._on_synced,None,None));a.results.put((lambda value:received.append(value),16,None))
  with patch.object(app.os.path,'exists',return_value=False):a._poll()
  self.assertEqual(received,[16]);self.assertTrue(a.results.empty());self.assertTrue(a.scheduled)
  self.assertFalse(a.syncing)
if __name__=='__main__':unittest.main()

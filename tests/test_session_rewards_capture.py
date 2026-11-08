import unittest,sys
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import session_reader
class CaptureTests(unittest.TestCase):
 def test_covered_log_is_unavailable(self):
  with patch('game_sync.find_game_window',return_value=(100,100,1100,900)),patch('PIL.ImageGrab.grab') as grab:
   self.assertIsNone(session_reader.capture_rewards([(850,700,1050,800)]));grab.assert_not_called()
 def test_crop_stays_in_game(self):
  with patch('game_sync.find_game_window',return_value=(100,100,1100,900)),patch('PIL.ImageGrab.grab',return_value=Image.new('RGB',(400,360))) as grab,patch('session_reader.read_reward_image',return_value=[]) as reader:
   self.assertEqual(session_reader.capture_rewards(),[]);self.assertEqual(grab.call_args.kwargs['bbox'],(700,500,1100,860));reader.assert_called_once()
 def test_no_game_no_capture(self):
  with patch('game_sync.find_game_window',return_value=None),patch('PIL.ImageGrab.grab') as grab:
   self.assertIsNone(session_reader.capture_rewards());grab.assert_not_called()
if __name__=='__main__':unittest.main()

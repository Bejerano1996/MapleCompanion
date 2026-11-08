import unittest,sys
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import session_reader
class CaptureTests(unittest.TestCase):
 def test_overlay_above_notices_does_not_disable_reader(self):
  with patch('game_sync.find_game_window',return_value=(100,100,1100,900)),patch('PIL.ImageGrab.grab',return_value=Image.new('RGB',(300,248))),patch('session_reader.read_reward_image',return_value=[('exp',56)]):
   self.assertEqual(session_reader.capture_rewards([(1000,200,1200,650)]),[('exp',56)])
 def test_covered_log_is_unavailable(self):
  with patch('game_sync.find_game_window',return_value=(100,100,1100,900)),patch('PIL.ImageGrab.grab') as grab:
   self.assertIsNone(session_reader.capture_rewards([(850,700,1050,800)]));grab.assert_not_called()
 def test_crop_stays_in_game(self):
  with patch('game_sync.find_game_window',return_value=(100,100,1100,900)),patch('PIL.ImageGrab.grab',return_value=Image.new('RGB',(400,360))) as grab,patch('session_reader.read_reward_image',return_value=[]) as reader:
   self.assertEqual(session_reader.capture_rewards(),[]);self.assertEqual(grab.call_args.kwargs['bbox'],(800,580,1100,828));reader.assert_called_once()
 def test_hud_can_be_read_when_log_is_covered(self):
  character={'level':27,'exp':31833,'percent':50,'need':63666}
  with patch('session_reader.capture_rewards',return_value=None),patch('game_sync.find_game_window',return_value=(100,100,1100,900)),patch('PIL.ImageGrab.grab',return_value=Image.new('RGB',(820,72))) as grab,patch('session_reader.read_character_image',return_value=character):
   result=session_reader.capture_training([(850,650,1050,750)],True)
   self.assertIsNone(result['events']);self.assertEqual(result['character'],character);self.assertEqual(grab.call_args.kwargs['bbox'],(200,828,1020,900))
 def test_log_only_poll_does_not_capture_hud(self):
  with patch('session_reader.capture_rewards',return_value=[]),patch('PIL.ImageGrab.grab') as grab:
   self.assertEqual(session_reader.capture_training(read_status=False),{'events':[],'character':None});grab.assert_not_called()
 def test_no_game_no_capture(self):
  with patch('game_sync.find_game_window',return_value=None),patch('PIL.ImageGrab.grab') as grab:
   self.assertIsNone(session_reader.capture_rewards());grab.assert_not_called()
if __name__=='__main__':unittest.main()

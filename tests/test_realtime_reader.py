import sys,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import session_reader as reader
from session_rewards import RewardTracker

class RealtimeReaderTests(unittest.TestCase):
    def setUp(self):
        reader._reward_ocr_cache=None

    def test_cached_pixels_still_confirm_money(self):
        image=Image.new('RGB',(200,40))
        rows=[([(1,1),(190,1),(190,15),(1,15)],'Gained Mesos (+27)',.90)]
        tracker=RewardTracker(confirm_money=2)
        tracker.feed([])
        with patch.object(reader,'ocr_rows',return_value=rows) as ocr:
            first=tracker.feed(reader.read_reward_image(image,True))
            second=tracker.feed(reader.read_reward_image(image,True))
        self.assertEqual((first['mesos'],second['mesos']),(0,27))
        self.assertEqual(ocr.call_count,1)

    def test_pixel_change_and_expiry_force_ocr(self):
        image=Image.new('RGB',(200,40))
        with patch.object(reader,'ocr_rows',return_value=[]) as ocr:
            with patch.object(reader.time,'monotonic',return_value=0):
                reader.read_reward_image(image)
                reader.read_reward_image(image)
                image.putpixel((10,10),(255,255,255))
                reader.read_reward_image(image)
            with patch.object(reader.time,'monotonic',return_value=2):
                reader.read_reward_image(image)
        self.assertEqual(ocr.call_count,3)

    def test_overlay_masks_only_covered_hud_pixels(self):
        image=Image.new('RGB',(1000,72),'white')
        with patch.object(reader,'capture_rewards',return_value=[]),patch('game_sync.find_game_window',return_value=(100,100,1100,900)),patch('PIL.ImageGrab.grab',return_value=image),patch.object(reader,'read_character_image',return_value=None) as read:
            reader.capture_training([(900,830,1100,900)])
        captured=read.call_args.args[0]
        self.assertEqual(captured.getpixel((0,20)),(255,255,255))
        self.assertEqual(captured.getpixel((900,20)),(0,0,0))

if __name__=='__main__':
    unittest.main()

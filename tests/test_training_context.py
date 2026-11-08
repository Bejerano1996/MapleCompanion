import unittest,sys
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from training_context import plausible_monsters,ContextTracker,visible_monsters,capture_context,party_rows,context_lines,map_from_title
from game_sync import find_minimap,minimap_title

class ContextTests(unittest.TestCase):
    def test_spawn_plausibility_distinguishes_unknown_and_empty(self):
        records={'known':{'monsters':[{'id':'24'}]},'empty':{'monsters':[]},'unknown':{},'bad':{'monsters':[{}]}}
        self.assertEqual(plausible_monsters([23,24],'known',records),[24])
        self.assertEqual(plausible_monsters([23],'empty',records),[])
        for map_id in ('missing','unknown','bad'):
            self.assertEqual(plausible_monsters([23],map_id,records),[23])
        self.assertEqual(plausible_monsters(['24'],'known',records),['24'])

    def test_confirm_and_expire_without_inventing_solo(self):
        t=ContextTracker();r=dict(game=True,map='a',party_visible=4,mobs=[1])
        self.assertIsNone(t.feed(r,0).get('map'))
        self.assertEqual(t.feed(r,8)['party_visible'],4)
        out=t.feed(dict(game=True,map=None,party_visible=None,mobs=[]),16)
        self.assertFalse(out['party_readable']);self.assertFalse(out['map_readable'])
        self.assertIsNone(t.feed(dict(game=True),30)['party_visible'])
        self.assertIsNone(t.feed(dict(game=True),30)['map'])
    def test_map_change_does_not_reuse_old_confirmation(self):
        t=ContextTracker();a=dict(game=True,map='a');b=dict(game=True,map='b')
        t.feed(a,0);t.feed(a,8)
        self.assertIsNone(t.feed(b,9)['map'])
        self.assertEqual(t.feed(b,17)['map'],'b')
        self.assertFalse(t.feed(None,18)['game'])
        self.assertIsNone(t.feed(b,19).get('map'))
    def test_only_actual_level_labels_match_monsters(self):
        mobs={1:dict(id=1,name='Ghost Stump',level=19),2:dict(id=2,name='Ghost Stump',level=20)}
        self.assertEqual(visible_monsters([dict(text='Lv.19 Ghost Stump',score=.99),dict(text='Hunt Ghost Stump',score=.99)],mobs),[1])
        self.assertFalse(visible_monsters([dict(text='Lv.19 Ghost Stump',score=.5)],mobs))
    def test_instruction_or_chat_prefix_is_not_a_visible_monster_label(self):
        mobs={1:dict(id=1,name='Ghost Stump',level=19)}
        for text in ('Hunt Lv.19 Ghost Stump','Player: Lv.19 Ghost Stump','Guide - Lv.19 Ghost Stump'):
            with self.subTest(text=text):self.assertEqual(visible_monsters([dict(text=text,score=.99)],mobs),[])
        self.assertEqual(visible_monsters([dict(text='  Lv.19 Ghost Stump',score=.99)],mobs),[1])
    def test_no_game_never_captures_desktop(self):
        with patch('game_sync.find_game_window',return_value=None),patch('PIL.ImageGrab.grab') as grab:
            self.assertEqual(capture_context({},{}),{'game':False});grab.assert_not_called()
    def test_recorded_party_has_four_visible_rows(self):
        im=Image.open(Path(__file__).parent/'context-party-four.png')
        self.assertEqual(party_rows(im,context_lines(im)),4)
        self.assertIsNone(party_rows(im,[]))
    def test_low_hp_members_are_not_dropped(self):
        im=Image.open(Path(__file__).parent/'context-party-five.png')
        self.assertEqual(party_rows(im,context_lines(im)),5)
    def test_recorded_visible_monster_label(self):
        image=Image.open(Path(__file__).parent/'live_sleepy.png');w,h=image.size
        scene=image.crop((int(w*.31),int(h*.18),int(w*.69),int(h*.88)))
        self.assertEqual(visible_monsters(context_lines(scene),{1:dict(id=1,name='Horny Mushroom',level=22)}),[1])
    def test_roman_map_variants_not_confused(self):
        maps={str(i):dict(id=str(i),displayName='Ant Tunnel '+'I'*i,displayStreet='Dungeon') for i in (1,2,3)}
        for name,expected in [('live_frame_ant_tunnel2.png','2'),('live_frame_1920.png','2'),('live_exp_2560.png','3')]:
            image=Image.open(Path(__file__).parent/name).convert('RGB')
            title=minimap_title(image,find_minimap(image))
            self.assertEqual(map_from_title(title,maps),expected)

if __name__=='__main__':unittest.main()

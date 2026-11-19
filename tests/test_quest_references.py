import unittest
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image

from quest_references import ReferenceIndex, VisibleReferences


def row(name, key='ccplz', slug='quest', exp=100):
    host = 'ccplz.cc' if key == 'ccplz' else 'maplestory-classic.com'
    return dict(name=name, provider=key, url='https://'+host+'/quests/'+slug, level=39, exp=exp)


class ReferenceTests(unittest.TestCase):
    def index(self, *rows):
        catalogs = SimpleNamespace(rows={})
        for item in rows:
            catalogs.rows.setdefault(item['provider'], []).append(item)
        index = ReferenceIndex()
        index.update(catalogs)
        return index

    def test_exact_alias_unifies_sources_without_merging_values(self):
        index = self.index(row('Chain (The New Quest)'), row('The New Quest', 'classic', exp=120))
        matches = index.match([{'text':'The New Quest'}])
        self.assertEqual(len(matches), 1)
        self.assertEqual({source['exp'] for source in matches[0]['sources']}, {100,120})

    def test_primary_quest_is_not_reported_missing(self):
        index = self.index(row('The New Quest'))
        self.assertEqual(index.match([{'text':'The New Quest'}], [{'name':'The New Quest'}]), [])

    def test_numbered_steps_and_truncated_titles_are_not_guessed(self):
        index = self.index(row('Find My Daughter 1'))
        for text in ['Find My Daughter 2', 'Find My Daughter…', 'Find My Daughter', 'Find My Daughtcr 1']:
            self.assertEqual(index.match([{'text':text}]), [])

    def test_ambiguous_same_provider_alias_is_not_guessed(self):
        index = self.index(row('Chain A (Becoming a Citizen)', slug='a'), row('Chain B (Becoming a Citizen)', slug='b'))
        self.assertEqual(index.match([{'text':'Becoming a Citizen'}]), [])
        self.assertEqual(len(index.match([{'text':'Chain A (Becoming a Citizen)'}])), 1)

    def test_repeated_ocr_passes_do_not_repeat_reference(self):
        index = self.index(row('The New Quest'))
        self.assertEqual(len(index.match([{'text':'The New Quest'}]*20)), 1)

    def test_chain_and_step_on_same_screen_do_not_duplicate_shared_quest(self):
        index=self.index(row('Chain (The New Quest)'),row('The New Quest','classic',exp=120))
        lines=[{'text':'Chain (The New Quest)'},{'text':'The New Quest'}]
        matches=index.match(lines)
        self.assertEqual(len(matches),1)
        self.assertEqual({source['exp'] for source in matches[0]['sources']},{100,120})

    def test_step_counter_alone_is_not_a_quest_title(self):
        index=self.index(row('[Event] Thanksgiving Pumpkin Pie (1 of 2)'))
        self.assertEqual(index.match([{'text':'1 of 2'}]),[])
        self.assertEqual(len(index.match([{'text':'[Event] Thanksgiving Pumpkin Pie (1 of 2)'}])),1)

    def test_two_fresh_reads_required_and_references_expire(self):
        tracker = VisibleReferences()
        refs = [dict(name='Quest', sources=[row('The New Quest')])]
        self.assertFalse(tracker.feed(refs, 0))
        self.assertTrue(tracker.feed(refs, 2))
        self.assertTrue(tracker.visible)
        self.assertFalse(tracker.feed([], 17))
        self.assertTrue(tracker.feed([], 17.01))
        self.assertEqual(tracker.visible, [])

    def test_stale_or_interrupted_candidates_cannot_confirm(self):
        refs = [dict(name='Quest', sources=[row('The New Quest')])]
        tracker = VisibleReferences()
        tracker.feed(refs, 0)
        tracker.feed(refs, 10.01)
        self.assertEqual(tracker.visible, [])
        tracker.feed([], 11)
        tracker.feed(refs, 12)
        self.assertEqual(tracker.visible, [])

    def test_manual_read_can_show_reference_and_clear_removes_it(self):
        tracker = VisibleReferences()
        self.assertTrue(tracker.feed([dict(name='Quest', sources=[row('The New Quest')])], 0, auto=False))
        self.assertTrue(tracker.clear())
        self.assertEqual(tracker.visible, [])

    def test_expiry_tick_does_not_interrupt_confirmation(self):
        tracker=VisibleReferences()
        refs=[dict(name='Quest',sources=[row('The New Quest')])]
        tracker.feed(refs,0)
        self.assertFalse(tracker.expire(1))
        self.assertTrue(tracker.feed(refs,2))
        self.assertTrue(tracker.expire(17.01))
        self.assertEqual(tracker.visible,[])

    def test_changed_source_exp_updates_visible_card_with_same_url(self):
        tracker=VisibleReferences()
        tracker.feed([dict(name='Quest',sources=[row('Quest',exp=100)])],0,auto=False)
        changed=tracker.feed([dict(name='Quest',sources=[row('Quest',exp=120)])],1,auto=False)
        self.assertTrue(changed)
        self.assertEqual(tracker.visible[0]['sources'][0]['exp'],120)

    def test_capture_returns_reference_without_creating_primary_id(self):
        import game_sync
        index = self.index(row('The New Quest'))
        catalog = SimpleNamespace(rows={'ccplz':[row('The New Quest')]})
        db = SimpleNamespace(quests={}, maps={}, reference_index=index, reference_catalogs=catalog)
        lines = [{'text':'The New Quest','x':600,'y':100,'w':200,'h':16},
                 {'text':'0 / 10 New Item','x':600,'y':125,'w':200,'h':16}]
        with patch.object(game_sync, 'find_game_window', return_value=(0,0,1024,768)), \
             patch('PIL.ImageGrab.grab', return_value=Image.new('RGB',(1024,768))), \
             patch.object(game_sync, 'find_minimap', return_value=None), \
             patch.object(game_sync, 'read_location', return_value=(None,'',False)), \
             patch('screen_ocr.passes', side_effect=lambda image:[image]), \
             patch('screen_ocr.read_lines', return_value=lines), \
             patch.object(game_sync, 'read_notices', return_value=[]):
            result = game_sync.capture_and_read(db,auto=True,exp_bar=False)
        self.assertEqual(result['quests'], [])
        self.assertEqual(result['tracked'], [])
        self.assertEqual(result['progress'], {})
        self.assertEqual(len(result['references']), 1)
        self.assertTrue(result['regions'])


if __name__ == '__main__':
    unittest.main()

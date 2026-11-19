import unittest
from unittest.mock import patch

import sync


class QuestMatchCacheTests(unittest.TestCase):
    def setUp(self):
        sync._match_quest_title.cache_clear()
        self.quests={'one':{'id':'one','name':'I Need to Find My Daughter 1'},
                     'two':{'id':'two','name':'I Need to Find My Daughter 2'}}

    def test_repeated_lines_reuse_decision_without_changing_scores(self):
        lines=[{'text':'I Need to Find My Daughter 1'}]
        with patch.object(sync,'title_score',wraps=sync.title_score) as score:
            first=sync.match_quests(lines,self.quests)
            calls=score.call_count
            for unused in range(30):
                self.assertEqual(sync.match_quests(lines,self.quests),first)
            self.assertEqual(score.call_count,calls)
        self.assertEqual(first,{'one':1.0})

    def test_catalog_edit_invalidates_cached_match(self):
        line=[{'text':'I Need to Find My Daughter 1'}]
        self.assertIn('one',sync.match_quests(line,self.quests))
        self.quests['one']['name']='Completely Different Quest'
        self.assertNotIn('one',sync.match_quests(line,self.quests))

    def test_number_ambiguity_is_not_hidden_by_cache(self):
        self.assertEqual(sync.match_quests([{'text':'I Need to Find My Daughter'}],self.quests),{})
        self.assertEqual(sync.match_quests([{'text':'I Need to Find My Daughter 2'}],self.quests),{'two':1.0})


if __name__=='__main__':
    unittest.main()

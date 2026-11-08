from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from monster_locations import monster_locations
from quest_rewards import reward_sections,reward_summary

class MapRewardTests(unittest.TestCase):
    def setUp(self):
        self.data={'a':{'name':'Near','monsters':[{'id':17,'count':4}]},'b':{'name':'Crowded','monsters':[{'id':17,'count':30}]},'c':{'name':'Island','monsters':[{'id':17,'count':80}]}}
    def test_spawn_sort_then_distance(self):
        rows=monster_locations(self.data,{},17,{'a':0,'b':3})
        self.assertEqual([r['map'] for r in rows],['b','a'])
        self.assertEqual((rows[1]['spawn'],rows[1]['distance']),(4,0))
    def test_nearest_sort(self):
        self.assertEqual([r['map'] for r in monster_locations(self.data,{},17,{'a':0,'b':3},sort='near')],['a','b'])
    def test_all_locations_not_limited_to_old_eight(self):
        data={str(i):{'monsters':[{'id':17,'count':i+1}]} for i in range(12)}
        rows=monster_locations(data,{},17,{str(i):11-i for i in range(12)},fallback=[['0','Old cached map']],sort='near')
        self.assertEqual(len(rows),12);self.assertEqual(rows[0]['map'],'11')
    def test_missing_data_is_not_reported_as_zero(self):
        row=monster_locations({}, {},17,{},fallback=[['x','Unknown']])[0]
        self.assertIsNone(row['spawn']);self.assertIsNone(row['distance'])
    def test_unknown_location_does_not_filter_every_map(self):
        self.assertEqual(len(monster_locations(self.data,{},17,{})),3)
    def test_random_and_choice_rewards_are_separate(self):
        q={'exp':1380,'mesos':614,'get':[{'name':'Potion','count':3}],
           'rewardRandom':[{'jobName':'Any Class','items':[{'name':'Garnet','count':1,'chance':12.5}]}],
           'rewardChoices':[{'items':[{'name':'Sword','count':1}]}]}
        sections=reward_sections(q)
        self.assertIn('3 × Potion',sections[0]['rows'])
        self.assertNotIn('Garnet',' '.join(sections[0]['rows']))
        self.assertIn('Choose',sections[1]['title']);self.assertIn('not guaranteed',sections[2]['title'])
        self.assertIn('12.5%',sections[2]['rows'][0])
        self.assertIn('Random item',reward_summary(q))
    def test_unknown_chance_is_not_zero_and_fame_sign_is_correct(self):
        q={'fame':-1,'rewardRandom':[{'items':[{'name':'Gem','count':1}]}]}
        sections=reward_sections(q)
        self.assertEqual(sections[0]['rows'],['-1 fame'])
        self.assertNotIn('%',sections[1]['rows'][0])
    def test_no_invented_rewards(self):
        self.assertEqual(reward_sections({}),[])
        self.assertEqual(reward_summary({}),'No reward listed')

if __name__=='__main__':unittest.main()

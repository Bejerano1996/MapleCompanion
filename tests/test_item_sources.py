from pathlib import Path
import sys,json,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import item_sources
from companion_planner_model import planner_objectives,planner_itinerary

class ItemSourceTests(unittest.TestCase):
    def test_real_salad_shops_keep_access_conditions(self):
        data=json.loads(Path(__file__).with_name('real-item-source-fixtures.json').read_text())['Salad']
        ranked=item_sources.ranked_sources(data,{'010005070':2,'010001007':0,'010007000':20})
        self.assertEqual(ranked[0]['npc'],'24 Hr Mobile Store')
        self.assertEqual(ranked[0]['price'],220)
        self.assertTrue(any(s.get('citizen')=='Visitor' for s in ranked))
    def test_real_plant_source_has_five_maps(self):
        data=json.loads(Path(__file__).with_name('real-item-source-fixtures.json').read_text())['Plant Sample']
        self.assertEqual(data[0]['name'],'Ellinia Flower')
        self.assertEqual(len(data[0]['maps']),5)
        self.assertTrue(data[0]['community'])
    def test_boxes_are_generic_and_unrelated_links_are_not_sources(self):
        page='0:'+json.dumps(['$', 'div',None,{'children':[['$','a',None,{'href':'/msclassic/breakables/9999999','children':'Unrelated'}],['$','h2',None,{'children':'Found in Breakables'}],['$','a',None,{'href':'/msclassic/breakables/0000000','children':'Wooden Box0000000▲ 4'}]]}])
        self.assertEqual(item_sources.breakable_links(page),[{'id':'0000000','name':'Wooden Box','href':'/msclassic/breakables/0000000'}])
    def test_spawn_maps_exclude_unknown_and_non_spawn_links(self):
        page='0:'+json.dumps(['$','div',None,{'children':[['$','a',None,{'href':'/msclassic/maps/9','children':'Unrelated'}],['$','h2',None,{'children':'Spawns on these maps (2)'}],['$','a',None,{'href':'/msclassic/maps/1','children':'Real'}],['$','a',None,{'href':'/msclassic/maps/2','children':'Removed'}]]}])
        self.assertEqual(item_sources.breakable_maps(page,{'1':{'displayName':'Real'},'9':{'displayName':'Other'}}),[['1','Real']])
    def test_nearest_source_map_is_used(self):
        source={'maps':[['a','A'],['b','B']]}
        self.assertEqual(item_sources.nearest_target(source,{'a':8,'b':2}),['b','B'])
    def test_shop_and_plant_objectives_are_planned_without_monsters(self):
        quests={'q':{'name':'Quest','need':[{'name':'Salad','itemId':1,'count':1},{'name':'Plant','itemId':2,'count':8}]}}
        guides={'q':[{'sources':[{'kind':'shop','maps':[['b','Shop']]}]},{'sources':[{'kind':'breakable','maps':[['c','Plant']]}]}]}
        objectives=planner_objectives({'active':['q']},quests,guides)
        plan=planner_itinerary('a',{'a':{'connectedMaps':[{'mapId':'b'}]},'b':{'connectedMaps':[{'mapId':'c'}]},'c':{}},objectives)
        self.assertEqual([row['map'] for row in plan['stops']],['b','c'])
        self.assertEqual(plan['unplanned'],[])
    def test_restricted_shop_is_not_silently_planned(self):
        objectives=planner_objectives({'active':['q']},{'q':{'need':[{'name':'Item','count':1}]}},{'q':[{'sources':[{'kind':'shop','citizen':'Visitor','maps':[['b','Shop']]}]}]})
        self.assertEqual(objectives[0]['source_maps'],[])

if __name__=='__main__':unittest.main()

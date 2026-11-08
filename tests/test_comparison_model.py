import unittest,copy
from companion_feature_model import utility_session_new,utility_session_track_map,utility_compare_maps

def completed(map_id,seconds,exp=0,mesos=0,cost=0,**extra):
    return dict(map_id=map_id,map_name=map_id,map_ids=[map_id],elapsed=seconds,exp=exp,
                mesos=mesos,cost=cost,kills=0,running_since=None,finished_at=100,**extra)

class ComparisonTests(unittest.TestCase):
    def test_first_map_does_not_mutate_session(self):
        source=utility_session_new(now=0);before=copy.deepcopy(source)
        tracked=utility_session_track_map(source,'A','Ant Tunnel',now=0)
        self.assertEqual(source,before)
        self.assertEqual(tracked['map_ids'],['A'])
        self.assertFalse(tracked.get('map_unattributed',False))
    def test_same_map_is_not_duplicated(self):
        session=utility_session_track_map(utility_session_new(now=0),'A',now=0)
        session=utility_session_track_map(session,'A',now=10)
        self.assertEqual(session['map_ids'],['A']);self.assertFalse(session['map_mixed'])
    def test_map_change_excludes_combined_totals(self):
        session=utility_session_track_map(utility_session_new(now=0),'A',now=0)
        session=utility_session_track_map(session,'B',now=1)
        session.update(finished_at=100,elapsed=100,exp=100)
        result=utility_compare_maps([session])
        self.assertEqual(result['maps'],[]);self.assertEqual(result['excluded']['mixed_maps'],1)
    def test_legacy_elapsed_time_cannot_be_assigned_retroactively(self):
        session=utility_session_new(now=0);session['elapsed']=100
        session=utility_session_track_map(session,'A',now=100)
        session['finished_at']=101
        self.assertTrue(session['map_unattributed'])
        self.assertEqual(utility_compare_maps([session])['excluded']['unknown_map'],1)
    def test_rates_are_weighted_by_total_recorded_time(self):
        history=[completed('A',600,100,400,100),completed('A',1800,900,200,300)]
        before=copy.deepcopy(history);row=utility_compare_maps(history)['maps'][0]
        self.assertEqual(history,before);self.assertEqual(row['sessions'],2)
        self.assertEqual(row['exp_hour'],1500);self.assertEqual(row['net_hour'],300)
    def test_invalid_unfinished_and_brief_records_do_not_make_rankings(self):
        records=[completed('A',0),completed('B',30),completed('C',100,float('nan')),
                 dict(elapsed=100,finished_at=1),dict(map_id='D',elapsed=100)]
        result=utility_compare_maps(records)
        self.assertEqual(result['maps'],[])
        self.assertEqual(result['below_minimum_maps'],1)
        self.assertEqual(sum(result['excluded'].values()),4)
    def test_net_sort_and_negative_profit(self):
        rows=utility_compare_maps([completed('A',3600,1000,100,300),completed('B',3600,100,500,0)],'net_hour')['maps']
        self.assertEqual([row['map_id'] for row in rows],['B','A'])
        self.assertEqual(rows[1]['net_hour'],-200)
    def test_malformed_map_history_is_not_ranked(self):
        session=completed('A',100)
        session['map_ids']=None
        self.assertEqual(utility_compare_maps([session])['excluded']['invalid'],1)
        tracked=utility_session_track_map(session,'B',now=100)
        self.assertTrue(tracked['map_unattributed'])
    def test_anchor_inconsistent_with_observed_map_is_mixed(self):
        session=completed('A',100)
        session['map_ids']=['B']
        self.assertEqual(utility_compare_maps([session])['excluded']['mixed_maps'],1)
    def test_null_finished_time_is_unfinished(self):
        session=completed('A',100);session['finished_at']=None
        self.assertEqual(utility_compare_maps([session])['excluded']['unfinished'],1)

if __name__=='__main__':unittest.main()

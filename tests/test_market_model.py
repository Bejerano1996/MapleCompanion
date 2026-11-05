"""Public market payload validation and rate-limit handling; no network required."""
from pathlib import Path
import sys,unittest
from urllib.error import HTTPError
from email.message import Message
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import companion_market as market

class MarketModelTests(unittest.TestCase):
    def test_unknown_price_is_never_zero(self):
        for value in (None,True,'100',-1,float('inf'),float('nan')):
            self.assertEqual(market.market_money(value),'Unavailable')
        self.assertEqual(market.market_money(0),'0')
    def test_invalid_payload_is_rejected(self):
        for value in (None,[],{}, {'items':None}, {'items':[None]}):
            with self.assertRaises(ValueError):market.market_payload(value)
    def test_normalization_does_not_mutate_source(self):
        original={'items':[None,{'name':'Test','range':9}]}
        self.assertEqual(market.market_payload(original)['items'],[{'name':'Test','range':[]}])
        self.assertEqual(original['items'][1]['range'],9)
    def test_empty_index_is_valid(self):
        self.assertEqual(market.market_payload({'items':[]})['items'],[])
    def test_retry_after_seconds(self):
        headers=Message();headers['Retry-After']='900'
        self.assertEqual(market.market_retry_delay(HTTPError('https://maplestory.watch',429,'Slow down',headers,None)),900)
    def test_retry_after_date(self):
        headers=Message();headers['Retry-After']='Thu, 01 Jan 1970 00:20:00 GMT'
        self.assertEqual(market.market_retry_delay(HTTPError('https://maplestory.watch',503,'Busy',headers,None),now=0),1200)
    def test_invalid_retry_header(self):
        for value in ('nan','-1','invalid'):
            headers=Message();headers['Retry-After']=value
            self.assertEqual(market.market_retry_delay(HTTPError('x',429,'Busy',headers,None)),300)
    def test_bad_timestamp_does_not_break_listing_deduplication(self):
        data={'listings':[{'unit':4,'seen':'invalid'},{'unit':4,'seen':5},{'unit':float('inf')}]}
        self.assertEqual(market.market_listings(data),[{'unit':4,'seen':5}])

if __name__=='__main__':unittest.main()

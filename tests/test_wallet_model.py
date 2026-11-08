import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wallet_model import checkpoint,balance
from companion_feature_model import utility_session_rates

class WalletTests(unittest.TestCase):
    def test_wallet_hour_rate_starts_at_wallet_baseline(self):
        s=checkpoint(dict(elapsed=600,wallet_elapsed_anchor=590),10100,10000)
        self.assertEqual(utility_session_rates(s)['net_hour'],36000)
    def test_checkpoints_replace_partial_notices(self):
        s=checkpoint(dict(mesos=12,cost=100),12500,10000)
        self.assertEqual(s['mesos'],2500)
        s=checkpoint(s,13000);self.assertEqual(s['mesos'],3000)
        self.assertEqual(utility_session_rates(s)['net_mesos'],3000)
    def test_spending_is_net_not_double_subtracted(self):
        s=checkpoint(dict(cost=500),9500,10000)
        self.assertEqual(utility_session_rates(s)['net_mesos'],-500)
    def test_invalid_inputs(self):
        for value in (True,'-1','1.5','nan',2147483648):
            with self.assertRaises(ValueError):balance(value)
    def test_exp_and_kills_preserved(self):
        s=checkpoint(dict(exp=123,kills=5),120,100)
        self.assertEqual((s['exp'],s['kills']),(123,5))
    def test_wallet_parser_real_probe(self):
        import json
        from session_reader import wallet_from_rows
        probe=Path(__file__).resolve().parents[2]/'wallet-ocr-probe.json'
        if not probe.exists():self.skipTest('Local live OCR probe absent')
        rows=[(b,t,c) for t,c,b in json.loads(probe.read_text(encoding='utf-8-sig'))]
        self.assertEqual(wallet_from_rows(rows),177906)
        self.assertIsNone(wallet_from_rows([r for r in rows if 'INVENTORY' not in r[1]]))

if __name__=='__main__':unittest.main()

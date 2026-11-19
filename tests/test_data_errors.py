import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data_errors import data_error_status
from meowdb import MeowDB,USER_AGENT


class DataErrorTests(unittest.TestCase):
    def test_http_errors_keep_the_actual_reason(self):
        self.assertIn('403',data_error_status('Error: HTTP Error 403: Forbidden'))
        self.assertIn('404',data_error_status("Error: <HTTPError 404: 'Not Found'>"))
        self.assertIn('rate limit',data_error_status('Error: HTTP Error 429: Too Many Requests'))
        self.assertIn('503',data_error_status('Error: HTTP Error 503: Unavailable'))

    def test_connection_and_tls_failures_are_distinct(self):
        self.assertIn('verification',data_error_status('Error: SSL certificate verify failed'))
        self.assertIn('timed out',data_error_status('Error: The operation timed out'))
        self.assertIn('connection',data_error_status('Error: getaddrinfo failed'))
        self.assertIn('Background task',data_error_status('Error: capture failed'))

    def test_outbound_agent_has_no_personal_identifier(self):
        self.assertTrue(USER_AGENT.startswith('UmbraleCompanion/'))
        self.assertNotIn('@',USER_AGENT)
        self.assertNotIn('gmail',USER_AGENT.casefold())
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            db=MeowDB(folder)
            response=MagicMock();response.__enter__.return_value.read.return_value=b'payload'
            with patch('meowdb.ACCESS_RENEWAL_REQUIRED',False),patch('meowdb._ACCESS_DENIED',None),patch('meowdb._LAST_REQUEST',None),patch('meowdb.urllib.request.urlopen',return_value=response) as call:
                self.assertEqual(db._fetch_once('/quest-tracker/10300'),b'payload')
            request=call.call_args.args[0]
            self.assertEqual(request.get_header('User-agent'),USER_AGENT)
            self.assertTrue(request.full_url.startswith('https://meowdb.com/'))


if __name__=='__main__':unittest.main()

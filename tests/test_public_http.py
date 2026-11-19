import unittest
from unittest.mock import patch
import urllib.request

from public_http import FixedOriginRedirect,ProviderRedirectError


class PublicHttpTests(unittest.TestCase):
    def setUp(self):
        self.request=urllib.request.Request('https://ccplz.cc/quests',headers={'User-Agent':'Fixture'})
        self.handler=FixedOriginRedirect(self.request.full_url)

    def redirect(self,url):
        return self.handler.redirect_request(self.request,None,302,'Found',{},url)

    def test_cross_origin_or_insecure_redirect_never_proceeds(self):
        for url in ('https://meowdb.com/msclassic','https://ccplz.cc.evil.test/quests',
                    'http://ccplz.cc/quests','https://ccplz.cc:444/quests','https://user@ccplz.cc/quests'):
            with self.subTest(url=url),patch('public_http.time.sleep') as sleep:
                with self.assertRaises(ProviderRedirectError):self.redirect(url)
                sleep.assert_not_called()

    def test_same_origin_canonical_redirect_obeys_rate_limit(self):
        with patch('public_http.time.sleep') as sleep:
            result=self.redirect('/quests/')
        self.assertEqual(result.full_url,'https://ccplz.cc/quests/')
        sleep.assert_called_once_with(10)


if __name__=='__main__':unittest.main()

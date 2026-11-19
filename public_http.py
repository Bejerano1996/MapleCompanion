"""Read public provider pages without following redirects to another origin."""
import time
import urllib.error
import urllib.parse
import urllib.request


class ProviderRedirectError(urllib.error.URLError):
    pass


def origin(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.username is not None or parsed.password is not None or not parsed.hostname:
        raise ProviderRedirectError('Provider redirect is not a public HTTPS address')
    return parsed.hostname.casefold(), parsed.port or 443


class FixedOriginRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self,url,min_interval=10):
        self.allowed=origin(url)
        self.min_interval=min_interval

    def redirect_request(self,request,fp,code,message,headers,new_url):
        new_url=urllib.parse.urljoin(request.full_url,new_url)
        if origin(new_url)!=self.allowed:
            raise ProviderRedirectError('Provider address changed origin; redirect not followed')
        redirected=super().redirect_request(request,fp,code,message,headers,new_url)
        # A redirect is another real HTTP request, so it obeys the same rate limit.
        if redirected is not None:
            time.sleep(self.min_interval)
        return redirected


def open_catalog_request(request,timeout=30):
    opener=urllib.request.build_opener(FixedOriginRedirect(request.full_url))
    return opener.open(request,timeout=timeout)

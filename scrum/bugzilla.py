import logging
import os
import xmlrpclib

from django.conf import settings
from django.core.cache import cache


log = logging.getLogger(__name__)
BZ_URL = getattr(settings, 'BUGZILLA_API_URL',
                 os.environ.get('BUGZILLA_API_URL',
                                'https://bugzilla.mozilla.org/xmlrpc.cgi'))
BZ_USER = getattr(settings, 'BUGZILLA_USER',
                  os.environ.get('BUGZILLA_USER'))
BZ_PASS = getattr(settings, 'BUGZILLA_PASS',
                  os.environ.get('BUGZILLA_PASS'))
SESSION_COOKIES_CACHE_KEY = 'bugzilla-session-cookies'


class SessionTransport(xmlrpclib.SafeTransport):
    """
    XML-RPC HTTPS transport that stores auth cookies in the cache.
    """
    _session_cookies = None

    @property
    def session_cookies(self):
        if self._session_cookies is None:
            cookie = cache.get(SESSION_COOKIES_CACHE_KEY)
            if cookie:
                self._session_cookies = cookie
        return self._session_cookies

    def parse_response(self, response):
        cookies = self.get_cookies(response)
        if cookies:
            self._session_cookies = cookies
            cache.set(SESSION_COOKIES_CACHE_KEY,
                      self._session_cookies, 0)
            log.debug('Got cookie: %s', self._session_cookies)
        return xmlrpclib.Transport.parse_response(self, response)

    def send_host(self, connection, host):
        cookies = self.session_cookies
        if cookies:
            for cookie in cookies:
                connection.putheader('Cookie', cookie)
                log.debug('Sent cookie: %s', cookie)
        return xmlrpclib.Transport.send_host(self, connection, host)

    def get_cookies(self, response):
        cookie_headers = None
        if hasattr(response, 'msg'):
            cookies = response.msg.getheaders('set-cookie')
            if cookies:
                log.debug('Full cookies: %s', cookies)
                cookie_headers = [c.split(';', 1)[0] for c in cookies]
        return cookie_headers


class BugzillaAPI(xmlrpclib.ServerProxy):
    def login(self, username=None, password=None):
        return self.User.login({
            'login': BZ_USER or username,
            'password': BZ_PASS or password,
            'remember': True,
        })


bugzilla = BugzillaAPI(BZ_URL, transport=SessionTransport(use_datetime=True),
                       allow_none=True)
if BZ_USER and not cache.get(SESSION_COOKIES_CACHE_KEY):
    bugzilla.login()

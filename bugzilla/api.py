import logging
import os
import xmlrpclib
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import make_aware, utc


def get_setting_or_env(name, default=None):
    """
    Return the setting or environment var name, or default.
    """
    return getattr(settings, name, os.environ.get(name, default))


log = logging.getLogger(__name__)
BZ_URL = get_setting_or_env('BUGZILLA_API_URL')
BZ_USER = get_setting_or_env('BUGZILLA_USER')
BZ_PASS = get_setting_or_env('BUGZILLA_PASS')
SESSION_COOKIES_CACHE_KEY = 'bugzilla-session-cookies'
PRODUCTS_CACHE = None
BUG_OPEN_STATUSES = settings.BUG_OPEN_STATUSES
BUG_CLOSED_STATUSES = settings.BUG_CLOSED_STATUSES
BZ_FIELDS = [
    'id',
    'status',
    'resolution',
    'summary',
    'whiteboard',
    'assigned_to',
    'priority',
    'severity',
    'product',
    'component',
    'blocks',
    'depends_on',
    'creation_time',
    'last_change_time',
    'target_milestone',
    'flags',
]
BZ_ATTACHMENT_FIELDS = [
    'file_name',
    'flags',
    'id',
    'is_patch',
    'is_obsolete',
]
UNWANTED_COMPONENT_FIELDS = [
    'sort_key',
    'is_active',
    'default_qa_contact',
    'default_assigned_to',
    'description',
    'flag_types',
]
UNWANTED_COMPONENT_FIELDS = ['components.' + i for i in UNWANTED_COMPONENT_FIELDS]


def clean_bug_data(bug):
    """
    Clean and prepare the data we get from Bugzilla for the db.

    :param data: dict of raw Bugzilla API data for a single bug.
    :return: dict of cleaned data for a single bug ready for the db.
    """
    # add UTC timezone info to dates.
    for k, v in bug.items():
        if isinstance(v, datetime):
            bug[k] = make_aware(v, utc)
    if 'history' in bug:
        for h in bug['history']:
            h['when'] = make_aware(h['when'], utc)


def is_closed(status):
    return status in BUG_CLOSED_STATUSES


def is_open(status):
    return status in BUG_OPEN_STATUSES


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
    _products_cache_key = 'bugzilla:products:components'

    def login(self, username=None, password=None):
        return self.User.login({
            'login': BZ_USER or username,
            'password': BZ_PASS or password,
            'remember': True,
        })

    def clear_products_cache(self):
        global PRODUCTS_CACHE
        PRODUCTS_CACHE = None
        cache.delete(self._products_cache_key)

    def get_products(self):
        global PRODUCTS_CACHE
        if PRODUCTS_CACHE is not None:
            return PRODUCTS_CACHE
        products = cache.get(self._products_cache_key)
        if products is None:
            prod_query = {
                'type': 'accessible',
                'include_fields': ['id', 'name', 'components'],
                'exclude_fields': UNWANTED_COMPONENT_FIELDS,
            }
            products = self.Product.get(prod_query)['products']
            cache.set(self._products_cache_key, products, 60 * 60 * 24 * 7)
        PRODUCTS_CACHE = products
        return products

    def get_products_simplified(self):
        products = self.get_products()
        simple = {}
        for p in products:
            simple[p['name']] = [c['name'] for c in p['components']]
        return simple

    def get_bug_ids(self, **kwargs):
        """
        Return a list of ids of bugs from a search
        """
        open_only = kwargs.pop('open_only', False)
        scrum_only = kwargs.pop('scrum_only', True)
        kwargs.update({
            'include_fields': ['id'],
        })
        if open_only and 'status' not in kwargs:
            kwargs['status'] = BUG_OPEN_STATUSES
        if scrum_only and 'whiteboard' not in kwargs:
            kwargs['whiteboard'] = ['u=', 'c=', 'p=']
        log.debug('Searching bugs with kwargs: %s', kwargs)
        bugs = self.Bug.search(kwargs)
        return [bug['id'] for bug in bugs.get('bugs', [])]

    def get_bugs(self, **kwargs):
        open_only = kwargs.pop('open_only', False)
        scrum_only = kwargs.pop('scrum_only', True)
        get_history = kwargs.pop('history', True)
        get_comments = kwargs.pop('comments', True)
        get_attachments = kwargs.pop('attachments', True)
        kwargs.update({
            'include_fields': BZ_FIELDS,
        })
        if 'ids' in kwargs:
            kwargs['permissive'] = True
            bugs = self.Bug.get(kwargs)
        else:
            if open_only and 'status' not in kwargs:
                kwargs['status'] = BUG_OPEN_STATUSES
            if scrum_only and 'whiteboard' not in kwargs:
                kwargs['whiteboard'] = ['u=', 'c=', 'p=']
            log.debug('Searching bugs with kwargs: %s', kwargs)
            bugs = self.Bug.search(kwargs)

        bug_ids = [bug['id'] for bug in bugs.get('bugs', [])]

        if not bug_ids:
            return bugs

        # mix in history, comments, and attachments
        history = comments = attachments = {}
        if get_history:
            history = self.get_history(bug_ids)
        if get_comments:
            comments = self.get_comments(bug_ids)
        if get_attachments:
            attachments = self.get_attachments(bug_ids)
        for bug in bugs['bugs']:
            bug['history'] = history.get(bug['id'], [])
            bug['comments_count'] = len(comments.get(bug['id'], {})
                                        .get('comments', []))
            bug['attachments'] = attachments.get(bug['id'], [])
            clean_bug_data(bug)
        return bugs

    def get_attachments(self, bug_ids):
        try:
            attachments = self.Bug.attachments({
                'ids': bug_ids,
                'include_fields': BZ_ATTACHMENT_FIELDS}).get('bugs')
        except xmlrpclib.Fault:
            log.exception('Problem getting attachments for bug ids: %s', bug_ids)
            return {}

        return dict((int(k), v) for k, v in attachments.iteritems())

    def get_history(self, bug_ids):
        try:
            history = self.Bug.history({'ids': bug_ids}).get('bugs')
        except xmlrpclib.Fault:
            log.exception('Problem getting history for bug ids: %s', bug_ids)
            return {}
        return dict((h['id'], h['history']) for h in history)

    def get_comments(self, bug_ids):
        try:
            comments = self.Bug.comments({
                'ids': bug_ids,
                'include_fields': ['id'],
                }).get('bugs')
        except xmlrpclib.Fault:
            log.exception('Problem getting comments for bug ids: %s', bug_ids)
            return {}
        return dict((int(bid), cids) for bid, cids in comments.iteritems())


bugzilla = BugzillaAPI(BZ_URL, transport=SessionTransport(use_datetime=True),
                       allow_none=True)

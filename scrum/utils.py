import hashlib
import os
import re
from calendar import timegm
from itertools import islice

from django.conf import settings
from django.http import QueryDict
from django.utils.encoding import smart_str
from django.utils.timezone import now

from dateutil.relativedelta import relativedelta


TAG_2_ATTR = {
    'p': 'points',
    'u': 'user',
    'c': 'component',
}
BZ_URL_EXCLUDE = (
#    'cmdtype',
#    'remaction',
#    'list_id',
    'columnlist',
)


# via https://github.com/mozilla/kitsune/blob/master/apps/search/utils.py#L38
# thanks willkg!
def chunked(iterable, n):
    """Returns chunks of n length of iterable

    If len(iterable) % n != 0, then the last chunk will have length
    less than n.

    Example:

    >>> chunked([1, 2, 3, 4, 5], 2)
    [(1, 2), (3, 4), (5,)]

    """
    iterable = iter(iterable)
    while 1:
        t = tuple(islice(iterable, n))
        if t:
            yield t
        else:
            return


def get_setting_or_env(name, default=None):
    """
    Return the setting or environment var name, or default.
    """
    return getattr(settings, name, os.environ.get(name, default))


WB_SPLIT_RE = re.compile(r'[\[\], ]+')


def parse_whiteboard(wb):
    wb_parts = WB_SPLIT_RE.split(wb.strip())
    if wb_parts:
        return dict(i.split('=', 1) for i in wb_parts if '=' in i)
    return {}


def get_story_data(wb):
    wb_dict = {
        'points': 0,
        'user': '',
        'component': '',
    }
    for k, v in parse_whiteboard(wb).iteritems():
        if v:
            cast = int if k == 'p' else str
            try:
                wb_dict[TAG_2_ATTR[k]] = cast(v)
            except (KeyError, ValueError):
                continue
    return wb_dict


def parse_bz_url(url):
    qs = url.split('?')[1]
    qd = QueryDict(qs, mutable=True)
    for key in BZ_URL_EXCLUDE:
        try:
            del qd[key]
        except KeyError:
            continue
    return qd


def get_bz_url_for_buglist(bugs):
    """Return a bugzilla search url that will display the list of bugs."""
    return get_bz_url_for_bug_ids(bug.id for bug in bugs)


def get_bz_url_for_bug_ids(bids):
    """Return a bugzilla search url that will display the list of bug ids."""
    bug_ids = ','.join(str(bid) for bid in bids)
    return '%sbug_id=%s&bug_id_type=anyexact' % (
        settings.BUGZILLA_SEARCH_URL,
        bug_ids
    )


def date_range(sdate, edate=None, step=1):
    """
    Return a list of date objects for every day
    between sdate and edate inclusive.
    """
    edate = edate or now().date()
    dates = []
    cdate = sdate
    while cdate <= edate:
        dates.append(cdate)
        cdate += relativedelta(days=step)
    return dates


def date_to_js(date):
    """Return unix epoc timestamp in miliseconds (in UTC)"""
    return timegm(date.timetuple()) * 1000


def make_sha1_key(key, key_prefix, version):
    """A cache key generating function that uses a sha1 hash."""
    prekey = ':'.join([key_prefix, str(version), smart_str(key)])
    return hashlib.sha1(prekey).hexdigest()

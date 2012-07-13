import hashlib
import time
from django.conf import settings

from django.http import QueryDict
from django.utils.encoding import smart_str

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
CLOSED_STATUSES = ['RESOLVED', 'VERIFIED']


def parse_whiteboard(wb):
    wb_dict = {
        'points': 0,
        'user': '',
        'component': '',
    }
    wb = wb.strip()
    if wb:
        data = dict(i.split('=') for i in wb.split() if '=' in i)
        for k, v in data.iteritems():
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
    bug_ids = ','.join(str(bug.id) for bug in bugs)
    return '%sbug_id=%s&bug_id_type=anyexact' % (
        settings.BZ_SEARCH_URL,
        bug_ids
    )


def is_closed(status):
    return status in CLOSED_STATUSES


def date_range(sdate, edate, step=1):
    """
    Return a list of date objects for every day
    between sdate and edate inclusive.
    """
    dates = []
    cdate = sdate
    while cdate <= edate:
        dates.append(cdate)
        cdate += relativedelta(days=step)
    return dates


def date_to_js(date):
    """Return unix epoc timestamp in miliseconds (in UTC)"""
    return int((time.mktime(date.timetuple()) - time.timezone) * 1000)


def make_sha1_key(key, key_prefix, version):
    """A cache key generating function that uses a sha1 hash."""
    prekey = ':'.join([key_prefix, str(version), smart_str(key)])
    return hashlib.sha1(prekey).hexdigest()

from time import mktime

from django.http import QueryDict

from dateutil.relativedelta import relativedelta


TAG_2_ATTR = {
    'p': 'points',
    'u': 'user',
    'c': 'component',
}
BZ_URL_EXCLUDE = (
    'cmdtype',
    'remaction',
    'list_id',
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
                wb_dict[TAG_2_ATTR[k]] = cast(v)
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


def is_closed(status):
    return status in CLOSED_STATUSES


def date_range(sdate, edate, step=1):
    """Return a list of date objects for every day between sdate and edate inclusive."""
    dates = []
    cdate = sdate
    while cdate <= edate:
        dates.append(cdate)
        cdate += relativedelta(days=step)
    return dates


def date_to_js(date):
    """Return unix epoc timestamp in miliseconds"""
    return int(mktime(date.timetuple()) * 1000)

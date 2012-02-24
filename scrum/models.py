import re
from collections import defaultdict
from datetime import datetime

import dateutil.parser
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.contrib import admin
from django.core.cache import cache
from django.core.validators import RegexValidator
from django.db import models
from django.http import QueryDict

import slumber


BZ_URL_EXCLUDE = (
    'cmdtype',
    'remaction',
    'list_id',
    'columnlist',
)
BZ_FIELDS = (
    'id',
    'url',
    'status',
    'summary',
    'history',
    'whiteboard',
    'assigned_to',
)
TAG_2_ATTR = {
    'p': 'points',
    'u': 'user',
    'c': 'component',
}
CLOSED_STATUSES = ['RESOLVED', 'VERIFIED']
BZAPI = slumber.API(settings.BZ_API_URL)
slug_re = re.compile(r'^[-.\w]+$')
validate_slug = RegexValidator(slug_re, "Enter a valid 'slug' consisting of letters, numbers, underscores, periods or hyphens.", 'invalid')


class Project(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField()

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return 'scrum_project', [self.slug]


class Sprint(models.Model):
    project = models.ForeignKey(Project, related_name='sprints')
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200, validators=[validate_slug])
    start_date = models.DateField()
    end_date = models.DateField()
    created_date = models.DateTimeField(editable=False, default=datetime.now)
    bz_url = models.URLField(verbose_name='Bugzilla URL', max_length=2048)

    class Meta:
        get_latest_by = 'created_date'
        ordering = ['-created_date']
        unique_together = ('project', 'slug')

    def __unicode__(self):
        return u'{0} - {1}'.format(self.project.name, self.name)

    @models.permalink
    def get_absolute_url(self):
        return 'scrum_sprint', (), {'pslug': self.project.slug,
                                    'sslug': self.slug}

    def _get_bz_args(self):
        """Return a dict of the arguments from the bz_url"""
        args = parse_bz_url(self.bz_url)
        args['include_fields'] = ','.join(BZ_FIELDS)
        return args

    def refresh_bugs(self):
        delattr(self, '_bugs')
        cache.delete(self._bugs_cache_key)
        return self.get_bugs()

    @property
    def _bugs_cache_key(self):
        return 'sprint:{0}:bugs'.format(self.pk)

    def get_bugs(self):
        if not hasattr(self, '_bugs'):
            data = cache.get(self._bugs_cache_key)
            if data is None:
                data = BZAPI.bug.get(**self._get_bz_args())
                cache.set(self._bugs_cache_key, data, 3600)
            self._bugs = [Bug(b) for b in data['bugs']]
        return self._bugs

    def get_time_series(self):
        now = datetime.now().date()
        sdate = self.start_date
        edate = self.end_date if self.end_date < now else now
        if sdate > now: return []
        tseries = []
        cdate = sdate
        while cdate <= edate:
            cpoints = 0
            for bug in self.get_bugs():
                cpoints += bug.points_for_date(cdate)
            tseries.append([cdate, cpoints])
            cdate = cdate + relativedelta(days=1)
        return tseries

    def get_bugs_data(self):
        data = {
            'users': defaultdict(int),
            'components': defaultdict(int),
            'status': defaultdict(int),
            'basic_status': defaultdict(int),
            'total_points': 0,
        }
        for bug in self.get_bugs():
            if bug.points:
                data['users'][bug.user] += bug.points
                data['components'][bug.component] += bug.points
                data['status'][bug.status] += bug.points
                data['basic_status'][bug.basic_status] += bug.points
                data['total_points'] += bug.points
        return data


class Bug(object):
    def __init__(self, data):
        for key, value in data.iteritems():
            setattr(self, key, value)
        for key, value in self.scrum_data.iteritems():
            setattr(self, key, value)

    def __getattr__(self, name):
        if name in BZ_FIELDS:
            return ''
        raise AttributeError(name)

    def is_closed(self):
        return is_closed(self.status)

    def is_assigned(self):
        return self.assigned_to['name'] != 'nobody'

    def points_for_date(self, date):
        cpoints = 0
        for h in self.points_history:
            if date < h['date']:
                return cpoints
            cpoints = h['points']
        return cpoints

    @property
    def basic_status(self):
        if self.is_closed():
            status = 'closed'
        else:
            status = 'assigned' if self.is_assigned() else 'open'
        return status

    @property
    def scrum_data(self):
        return parse_whiteboard(self.whiteboard)

    @property
    def points_history(self):
        if not hasattr(self, '_phistory'):
            phistory = []
            cpoints = 0
            closed = False
            for h in self.history:
                hdate = dateutil.parser.parse(h['change_time']).date()
                for change in h['changes']:
                    fn = change['field_name']
                    if fn == 'status':
                        now_closed = is_closed(change['added'])
                        if closed != now_closed:
                            pts = 0 if now_closed else cpoints
                            phistory.append({
                                'date': hdate,
                                'points': pts,
                            })
                            closed = now_closed
                    elif fn == 'whiteboard':
                        pts = parse_whiteboard(change['added'])['points']
                        if pts != cpoints:
                            cpoints = pts
                            if not closed:
                                phistory.append({
                                    'date': hdate,
                                    'points': pts,
                                })
            self._phistory = phistory
        return self._phistory



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


admin.site.register(Project)
admin.site.register(Sprint)

from __future__ import absolute_import

import re
from collections import defaultdict
from datetime import datetime

from django.conf import settings
from django.contrib import admin
from django.core.cache import cache
from django.core.validators import RegexValidator
from django.db import models

import dateutil.parser
import slumber

from .utils import (date_to_js, is_closed, date_range, parse_bz_url,
                    parse_whiteboard)


BZ_FIELDS = (
    'id',
    'url',
    'status',
    'summary',
    'history',
    'whiteboard',
    'assigned_to',
)
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

    def get_burndown(self):
        """Return a list of total point values per day of sprint"""
        now = datetime.utcnow().date()
        sdate = self.start_date
        edate = self.end_date if self.end_date < now else now
        if sdate > now: return []
        tseries = []
        for cdate in date_range(sdate, edate):
            cpoints = 0
            for bug in self.get_bugs():
                cpoints += bug.points_for_date(cdate)
            tseries.append([date_to_js(cdate), cpoints])
        return tseries

    def get_burndown_axis(self):
        """Return a list of epoch dates between sprint start and end inclusive"""
        return [date_to_js(cdate) for cdate in
                date_range(self.start_date, self.end_date)]

    def get_bugs_data(self):
        data = {
            'users': defaultdict(int),
            'components': defaultdict(int),
            'status': defaultdict(int),
            'basic_status': defaultdict(int),
            'total_points': 0,
            'burndown': self.get_burndown(),
            'burndown_axis': self.get_burndown_axis(),
        }
        for bug in self.get_bugs():
            if bug.points:
                data['users'][bug.user] += bug.points
                data['components'][bug.component] += bug.points
                data['status'][bug.status] += bug.points
                data['basic_status'][bug.basic_status] += bug.points
                data['total_points'] += bug.points
        # have to convert to dicts b/c of django template bug
        for item in ['users', 'components', 'status', 'basic_status']:
            data[item] = dict(data[item])
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


admin.site.register(Project)
admin.site.register(Sprint)

from __future__ import absolute_import

import re
from collections import defaultdict
from datetime import datetime

from django.conf import settings
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
    'priority',
    'product',
    'component',
)
BZAPI = slumber.API(settings.BZ_API_URL)
slug_re = re.compile(r'^[-.\w]+$')
validate_slug = RegexValidator(slug_re, "Enter a valid 'slug' consisting of "
                               "letters, numbers, underscores, periods or "
                               "hyphens.", 'invalid')
CACHE_BUGS_FOR = getattr(settings, 'CACHE_BUGS_FOR', 2) * 60 * 60  # hours


class BZError(IOError):
    """Bugzilla connection error"""


class Project(models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=50, validators=[validate_slug],
                            db_index=True, unique=True)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return 'scrum_project', [self.slug]

    @models.permalink
    def get_edit_url(self):
        return 'scrum_project_edit', [self.slug]


class Sprint(models.Model):
    project = models.ForeignKey(Project, related_name='sprints')
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200, validators=[validate_slug],
                            db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    created_date = models.DateTimeField(editable=False, default=datetime.now)

    date_cached = None

    class Meta:
        get_latest_by = 'created_date'
        ordering = ['-start_date']
        unique_together = ('project', 'slug')

    def __unicode__(self):
        return u'{0} - {1}'.format(self.project.name, self.name)

    @models.permalink
    def get_absolute_url(self):
        return 'scrum_sprint', (), {'pslug': self.project.slug,
                                    'sslug': self.slug}

    @models.permalink
    def get_edit_url(self):
        return 'scrum_sprint_edit', (), {'pslug': self.project.slug,
                                         'sslug': self.slug}

    def get_burndown(self):
        """Return a list of total point values per day of sprint"""
        now = datetime.utcnow().date()
        sdate = self.start_date
        edate = self.end_date if self.end_date < now else now
        if sdate > now:
            return []
        tseries = []
        for cdate in date_range(sdate, edate):
            cpoints = 0
            for bug in self.get_bugs():
                cpoints += bug.points_for_date(cdate)
            tseries.append([date_to_js(cdate), cpoints])
        return tseries

    def get_burndown_axis(self):
        """Return a list of epoch dates between sprint start and end
        inclusive"""
        return [date_to_js(cdate) for cdate in
                date_range(self.start_date, self.end_date)]

    def get_bugs(self, refresh=False):
        """Get a unique set of bugs from all bz urls"""
        return self._get_url_items('bugs', refresh)

    def get_components(self):
        """Get a unique set of bugs from all bz urls"""
        return self._get_url_items('components')

    def get_products(self):
        """Get a unique set of bugs from all bz urls"""
        return self._get_url_items('products')

    def _get_url_items(self, item_name, *args):
        """Get a unique set of items from all bz urls"""
        items = set()
        for url in self.urls.all():
            items |= getattr(url, 'get_' + item_name)(*args)
            if url.date_cached:
                self.date_cached = url.date_cached
        return list(items)

    def get_bugs_data(self):
        bugs = self.get_bugs()
        data = {
            'users': defaultdict(int),
            'components': defaultdict(int),
            'status': defaultdict(int),
            'basic_status': defaultdict(int),
            'total_points': 0,
            'total_bugs': len(bugs),
            'scoreless_bugs': 0,
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
            else:
                data['scoreless_bugs'] += 1
        return data

    def save(self, force_insert=False, force_update=False, using=None):
        """Clear the cache if we update the bz url"""
        if self.pk:
            old_obj = Sprint.objects.get(pk=self.pk)
            if old_obj.bz_url != self.bz_url:
                self.refresh_bugs()
        return super(Sprint, self).save(force_insert, force_update, using)


class BugzillaURL(models.Model):
    url = models.URLField(verbose_name='Bugzilla URL', max_length=2048)
    project = models.ForeignKey(Project, null=True, blank=True,
                                related_name='urls')
    sprint = models.ForeignKey(Sprint, null=True, blank=True,
                               related_name='urls')

    date_cached = None

    def set_project_or_sprint(self, obj, obj_type=None):
        """Figure out if obj is a project or sprint, and set it as such."""
        if obj_type is None:
            obj_type = obj._meta.module_name
        setattr(self, obj_type, obj)

    def _get_bz_args(self):
        """Return a dict of the arguments from the bz_url"""
        args = parse_bz_url(self.url)
        args['include_fields'] = ','.join(BZ_FIELDS)
        return args

    def _clear_cache(self):
        try:
            delattr(self, '_bugs')
        except AttributeError:
            pass
        cache.delete(self._bugs_cache_key)

    @property
    def _bugs_cache_key(self):
        return 'url:{0}:bugs'.format(self.pk)

    def get_bugs(self, refresh=False):
        if refresh:
            self._clear_cache()
        if not hasattr(self, '_bugs'):
            data = cache.get(self._bugs_cache_key)
            if data is None:
                try:
                    data = BZAPI.bug.get(**self._get_bz_args())
                    data['date_received'] = datetime.now()
                    cache.set(self._bugs_cache_key, data, CACHE_BUGS_FOR)
                except:
                    raise BZError("Couldn't retrieve bugs from "
                                  "Bugzilla")
            self._bugs = set(Bug(b) for b in data['bugs'])
            self.date_cached = data.get('date_received', datetime.now())
        return self._bugs

    def get_products(self):
        """Return a set of the products in the search url"""
        return set(self._get_bz_args().getlist('product'))

    def get_components(self):
        """Return a set of the components in the search url"""
        return set(self._get_bz_args().getlist('component'))


class Bug(object):
    def __init__(self, data):
        for key, value in data.iteritems():
            if key == 'component':
                setattr(self, 'bz_component', value)
            else:
                setattr(self, key, value)
        for key, value in self.scrum_data.iteritems():
            setattr(self, key, value)

    def __getattr__(self, name):
        if name in BZ_FIELDS:
            return ''
        raise AttributeError(name)

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return int(self.id)

    def is_closed(self):
        return is_closed(self.status)

    def is_assigned(self):
        return self.assigned_to['name'] != 'nobody'

    def points_for_date(self, date):
        cpoints = self.points
        for h in self.points_history:
            if date < h['date']:
                return cpoints
            cpoints = h['points']
        return cpoints

    @property
    def basic_status(self):
        if not self.points:
            status = 'scoreless'
        elif self.is_closed():
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

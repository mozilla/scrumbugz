from __future__ import absolute_import

import hashlib
from django.utils.decorators import method_decorator
import re
from collections import defaultdict
from datetime import datetime
from operator import itemgetter

from django.conf import settings
from django.core.cache import cache
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver

import dateutil.parser
import slumber
from jsonfield import JSONField

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


class BugsMixin(object):
    num_no_data_bugs = 0

    def get_bugs(self, refresh=False, scrum_only=True):
        """Get a unique set of bugs from all bz urls"""
        return self._get_url_items('bugs', refresh, scrum_only)

    def get_components(self):
        """Get a unique set of bugs from all bz urls"""
        return self._get_url_items('components')

    def get_products(self):
        """Get a unique set of bugs from all bz urls"""
        return self._get_url_items('products')

    def _get_url_items(self, item_name, *args):
        """Get a unique set of items from all bz urls"""
        attr_name = "_url_items_%s" % item_name
        if not hasattr(self, attr_name):
            items = set()
            for url in self.urls.all():
                items |= getattr(url, 'get_' + item_name)(*args)
                if url.date_cached:
                    self.date_cached = url.date_cached
                if item_name == 'bugs' and url.num_no_data_bugs:
                    self.num_no_data_bugs += url.num_no_data_bugs

            setattr(self, attr_name, list(items))
        return getattr(self, attr_name)

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
        }
        for bug in bugs:
            if bug.story_points:
                data['users'][bug.story_user] += bug.story_points
                data['components'][bug.story_component] += bug.story_points
                data['status'][bug.status] += bug.story_points
                data['basic_status'][bug.basic_status] += bug.story_points
                data['total_points'] += bug.story_points
            else:
                data['scoreless_bugs'] += 1
        return data

    def get_graph_bug_data(self):
        data = self.get_bugs_data()
        for item in ['users', 'components', 'status', 'basic_status']:
            data[item] = [{'label': k, 'data': v} for k, v in
                                                  sorted(data[item].iteritems(),
                                                         key=itemgetter(1),
                                                         reverse=True)]
        return data


class Project(BugsMixin, models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=50, validators=[validate_slug],
                            db_index=True, unique=True)
    has_backlog = models.BooleanField('Use a backlog', default=False)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return 'scrum_project', [self.slug]

    @models.permalink
    def get_edit_url(self):
        return 'scrum_project_edit', [self.slug]


class Sprint(BugsMixin, models.Model):
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

    def get_burndown_data(self):
        return {
            'burndown': self.get_burndown(),
            'burndown_axis': self.get_burndown_axis(),
        }


def extract_bug_kwargs(data):
    kwargs = data.copy()
    if 'history' in kwargs:
        del kwargs['history']
    kwargs['assigned_to'] = kwargs['assigned_to']['name']
    if 'url' in kwargs:
        del kwargs['url']
    if 'whiteboard' in kwargs:
        scrum_data = parse_whiteboard(kwargs['whiteboard'])
        for key, val in scrum_data.iteritems():
            if val:
                kwargs['story_' + key] = val
    return kwargs


class CachedBugManager(models.Manager):
    @method_decorator(transaction.commit_on_success)
    def store_bugs(self, bugs):
        from pprint import pprint
        for bug in bugs:
            pprint(bug)
            self.update_or_create(bug)

    def update_or_create(self, data):
        """
        Create or overwrite a bug from the given data.
        :param data: dict of bug data
        :return: CachedBug instance
        """
        obj = self.model(data=data)
        obj.save()
        return obj


class CachedBug(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    data = JSONField()
    last_updated = models.DateTimeField(default=datetime.now)
    product = models.CharField(max_length=200)
    component = models.CharField(max_length=200)
    assigned_to = models.CharField(max_length=200)
    status = models.CharField(max_length=20)
    summary = models.CharField(max_length=500)
    priority = models.CharField(max_length=2, blank=True)
    whiteboard = models.CharField(max_length=200, blank=True)
    story_user = models.CharField(max_length=50, blank=True)
    story_component = models.CharField(max_length=50, blank=True)
    story_points = models.PositiveSmallIntegerField(default=0)

    objects = CachedBugManager()

    @property
    def scrum_data(self):
        return parse_whiteboard(self.whiteboard)

    def fill_from_data(self):
        self.__dict__.update(extract_bug_kwargs(self.data))


@receiver(pre_save, sender=CachedBug)
def fill_bug_fields(sender, instance, **args):
    instance.fill_from_data()


class BugzillaURL(models.Model):
    url = models.URLField(verbose_name='Bugzilla URL', max_length=2048)
    project = models.ForeignKey(Project, null=True, blank=True,
                                related_name='urls')
    sprint = models.ForeignKey(Sprint, null=True, blank=True,
                               related_name='urls')

    date_cached = None
    num_no_data_bugs = 0

    class Meta:
        ordering = ('id',)

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
        return hashlib.sha1(self.url).hexdigest()

    def get_bugs(self, refresh=False, scrum_only=True):
        if refresh:
            self._clear_cache()
        if not hasattr(self, '_bugs'):
            data = cache.get(self._bugs_cache_key)
            if data is None:
                try:
                    args = self._get_bz_args()
                    args = dict((k.encode('utf-8'), v) for k, v in
                                args.iterlists())
                    data = BZAPI.bug.get(**args)
                    data['date_received'] = datetime.now()
                except:
                    raise BZError("Couldn't retrieve bugs from Bugzilla")
                cache.set(self._bugs_cache_key, data, CACHE_BUGS_FOR)
                CachedBug.objects.store_bugs(data['bugs'])
            self._bugs = set(Bug(b) for b in data['bugs'])
            if scrum_only:
                # only show bugs that have at least user and component set
                num_all_bugs = len(self._bugs)
                self._bugs = set(b for b in self._bugs
                                 if b.has_scrum_data)
                self.num_no_data_bugs = num_all_bugs - len(self._bugs)
            self.date_cached = data.get('date_received', datetime.now())
        return self._bugs

    def get_products(self):
        """Return a set of the products in the search url"""
        return set(self._get_bz_args().getlist('product'))

    def get_components(self):
        """Return a set of the components in the search url"""
        return set(self._get_bz_args().getlist('component'))

    def get_whiteboard(self):
        return self._get_bz_args().get('status_whiteboard')


class Bug(object):
    def __init__(self, data):
        self.__dict__.update(data)
        for key, value in self.scrum_data.iteritems():
            setattr(self, 'story_' + key, value)

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
        cpoints = self.story_points
        for h in self.points_history:
            if date < h['date']:
                return cpoints
            cpoints = h['points']
        return cpoints

    @property
    def basic_status(self):
        if not self.has_scrum_data:
            status = 'dataless'
        elif not self.story_points:
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
    def has_scrum_data(self):
        return bool(self.story_user and self.story_component)

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

from __future__ import absolute_import

import hashlib
import re
import zlib
from base64 import b64decode, b64encode
from collections import defaultdict
from datetime import datetime
from markdown import markdown
from operator import itemgetter

from django.conf import settings
from django.core.cache import cache
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.encoding import force_unicode

import dateutil.parser
import slumber
from jsonfield import JSONField
from scrum.utils import get_bz_url_for_buglist

from .utils import (date_to_js, is_closed, date_range, parse_bz_url,
                    parse_whiteboard)


class CompressedJSONField(JSONField):
    """
    Django model field that stores JSON data compressed with zlib.
    """
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = zlib.decompress(b64decode(value))
            except zlib.error:
                # must not be compressed. leave alone.
                pass
        return super(CompressedJSONField, self).to_python(value)

    def get_db_prep_value(self, value, connection=None, prepared=None):
        value = super(CompressedJSONField, self).get_db_prep_value(value,
                                                                   connection,
                                                                   prepared)
        return b64encode(zlib.compress(value, 9))


try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ['^scrum\.models\.CompressedJSONField'])
except ImportError:
    pass


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


class BugsListMixin(object):
    num_no_data_bugs = 0

    def get_bugs(self, **kwargs):
        """Get a unique set of bugs from all bz urls"""
        self.scrum_only = kwargs.get('scrum_only', True)
        if kwargs.get('refresh', False):
            self._clear_bugs_data_cache()
        return self._get_url_items('bugs', **kwargs)

    def get_components(self):
        """Get a unique set of bugs from all bz urls"""
        return self._get_url_items('components')

    def get_products(self):
        """Get a unique set of bugs from all bz urls"""
        return self._get_url_items('products')

    def _get_url_items(self, item_name, **kwargs):
        """Get a unique set of items from all bz urls"""
        attr_name = "_url_items_%s" % item_name
        if kwargs.get('refresh', False) and hasattr(self, attr_name):
            delattr(self, attr_name)
        if not hasattr(self, attr_name):
            items = set()
            for url in self.get_urls():
                items |= getattr(url, 'get_' + item_name)(**kwargs)

                if url.date_cached:
                    self.date_cached = url.date_cached
                if item_name == 'bugs' and url.num_no_data_bugs:
                    self.num_no_data_bugs += url.num_no_data_bugs

            setattr(self, attr_name, list(items))
        return getattr(self, attr_name)

    def _get_bugs_data(self):
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
        data['points_remaining'] = (data['total_points'] -
                                    data['basic_status']['closed'])
        return data

    @property
    def _bugs_data_cache_key(self):
        return '%s:%d:bugs_data' % (self._meta.module_name, self.id)

    def _clear_bugs_data_cache(self):
        cache.delete(self._bugs_data_cache_key)

    def get_bugs_data(self):
        # caching this for storage in the model (for fast display in lists)
        data = cache.get(self._bugs_data_cache_key)
        if data is None:
            data = self._get_bugs_data()
            cache.set(self._bugs_data_cache_key, data, CACHE_BUGS_FOR)
            if hasattr(self, 'bugs_data_cache'):
                self.bugs_data_cache = data
                self.save()
        return data

    def get_graph_bug_data(self):
        data = self.get_bugs_data()
        for item in ['users', 'components', 'status', 'basic_status']:
            data[item] = [{'label': k, 'data': v} for k, v in
                          sorted(data[item].iteritems(), key=itemgetter(1),
                                 reverse=True)]
        return data


class Team(models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=50, validators=[validate_slug],
                            db_index=True, unique=True)


class Project(BugsListMixin, models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=50, validators=[validate_slug],
                            db_index=True, unique=True)
    has_backlog = models.BooleanField('Use a backlog', default=False)
    team = models.ForeignKey(Team, related_name='projects', null=True)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return 'scrum_project', [self.slug]

    @models.permalink
    def get_edit_url(self):
        return 'scrum_project_edit', [self.slug]

    def get_backlog(self):
        """
        Return a list of bugs from this project's backlog not in any sprint.
        :param sprint: a Sprint instance
        :return: list of bug objects
        """
        backlog = self.get_bugs()
        backlog_ids = [bug.id for bug in backlog]
        return Bug.objects.filter(id__in=backlog_ids,
                                        sprint__isnull=True)

    def get_urls(self):
        return self.urls.all()


class Sprint(BugsListMixin, models.Model):
    project = models.ForeignKey(Project, related_name='sprints')
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200, validators=[validate_slug],
                            db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    notes = models.TextField(blank=True, help_text='This field uses '
        '<a href="http://daringfireball.net/projects/markdown/syntax"'
        'target="_blank">Markdown syntax</a> for conversion to HTML.')
    notes_html = models.TextField(blank=True, editable=False)
    created_date = models.DateTimeField(editable=False, default=datetime.now)
    bz_url = models.URLField(verbose_name='Bugzilla URL', max_length=2048,
                             null=True, blank=True)
    bugs_data_cache = JSONField(editable=False, null=True)

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

    def get_urls(self):
        """
        Get a list of BugzillaURL objects plus one for manually added bugs.
        """
        urls = list(self.urls.all())
        bugs = self.cached_bugs.all()
        if bugs:
            urls += [BugzillaURL(url=get_bz_url_for_buglist(bugs))]
        return urls

    def update_bugs(self, bug_ids, manual=False):
        """
        Add and remove bugs to sync the list with what we receive.
        :param bug_ids: list of bugs or bug ids
        :return: None
        """
        if not isinstance(bug_ids[0], (basestring, int)):
            bug_ids = [bug.id for bug in bug_ids]
        current_bugs = set(self.cached_bugs.all())
        new_bugs = set(Bug.objects.filter(id__in=bug_ids))
        to_add = new_bugs - current_bugs
        to_remove = current_bugs - new_bugs
        # saving individually to fire signals
        for bug in to_add:
            if bug.sprint and bug.added_manually:
                continue
            bug.sprint = self
            bug.added_manually = manual
            bug.save()
        for bug in to_remove:
            if bug.sprint and bug.added_manually and not manual:
                continue
            bug.sprint = None
            bug.added_manually = False
            bug.save()

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

    def get_cached_bugs_data(self):
        # TODO: Process this in some way if None
        return self.bugs_data_cache


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

    def _get_bugs_from_api(self):
        """Do the actual work of getting bugs from the BZ API"""
        try:
            args = self._get_bz_args()
            args = dict((k.encode('utf-8'), v) for k, v in
                args.iterlists())
            data = BZAPI.bug.get(**args)
            data['date_received'] = datetime.now()
        except Exception:
            raise BZError("Couldn't retrieve bugs from Bugzilla")
        return data

    def get_bugs(self, refresh=False, scrum_only=True):
        if refresh:
            self._clear_cache()
        if not hasattr(self, '_bugs'):
            cached_data = cache.get(self._bugs_cache_key)
            if not cached_data:
                data = self._get_bugs_from_api()
                cache.set(self._bugs_cache_key, {
                    'date_received': data['date_received'],
                    'bug_ids': [int(bug['id']) for bug in data['bugs']],
                }, CACHE_BUGS_FOR)
                self._bugs = set(store_bugs(data['bugs'], self.sprint))
                self.date_cached = data['date_received']
            else:
                self._bugs = set(Bug.objects.filter(
                    id__in=cached_data['bug_ids'])
                )
                self.date_cached = cached_data['date_received']
            if scrum_only:
                # only show bugs that have at least user and component set
                num_all_bugs = len(self._bugs)
                self._bugs = set(b for b in self._bugs
                                 if b.has_scrum_data)
                self.num_no_data_bugs = num_all_bugs - len(self._bugs)
            self.scrum_only = scrum_only
        return self._bugs

    def get_products(self):
        """Return a set of the products in the search url"""
        return set(self._get_bz_args().getlist('product'))

    def get_components(self):
        """Return a set of the components in the search url"""
        return set(self._get_bz_args().getlist('component'))

    def get_whiteboard(self):
        return self._get_bz_args().get('status_whiteboard')


class BugManager(models.Manager):
    def update_or_create(self, data):
        """
        Create or update a cached bug from the data returned from Bugzilla.
        :param data: dict of bug data from the bugzilla api.
        :return: Bug instance, boolean created.
        """
        bid = data.copy().pop('id')
        defaults = extract_bug_kwargs(data)
        bug, created = self.get_or_create(id=bid, defaults=defaults)
        if not created:
            bug.fill_from_data(defaults)
            bug.save()
        return bug, created


class Bug(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    history = CompressedJSONField()
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

    added_manually = models.BooleanField()
    sprint = models.ForeignKey(Sprint, related_name='cached_bugs', null=True,
                               on_delete=models.SET_NULL)

    objects = BugManager()

    class Meta:
        ordering = ('id',)

    def __unicode__(self):
        return unicode(self.id)

    def fill_from_data(self, data):
        self.__dict__.update(data)
        self.last_updated = datetime.now()

    def refresh_from_bugzilla(self):
        data = BZAPI.bug.get(
            id=self.id,
            id_mode='include',
            include_fields=','.join(BZ_FIELDS),
        )
        self.fill_from_data(data['bugs'][0])

    def get_absolute_url(self):
        return '%sid=%s' % (settings.BZ_SHOW_URL, self.id)

    def is_closed(self):
        return is_closed(self.status)

    def is_assigned(self):
        if isinstance(self.assigned_to, dict):
            return self.assigned_to['name'] != 'nobody'
        return self.assigned_to != 'nobody'

    def points_for_date(self, date):
        cpoints = self.story_points
        for h in self.points_history:
            if date < h['date']:
                return cpoints
            cpoints = h['points']
        return cpoints

    def _parse_assigned(self):
        return self.assigned_to.split('||', 1)

    @property
    def assigned_name(self):
        return self._parse_assigned()[0]

    @property
    def assigned_real_name(self):
        return self._parse_assigned()[-1]

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
        return bool(self.story_points or
                    self.story_user or
                    self.story_component)

    @property
    def points_history(self):
        if not hasattr(self, '_points_history'):
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
            self._points_history = phistory
        return self._points_history


class BugSprintLogManager(models.Manager):
    def _record_action(self, bug, sprint, action, manual):
        self.create(bug=bug, sprint=sprint, action=action,
                    manual=manual)

    def added_to_sprint(self, bug, sprint, manual):
        self._record_action(bug, sprint, BugSprintLog.ADDED, manual)

    def removed_from_sprint(self, bug, sprint, manual):
        self._record_action(bug, sprint, BugSprintLog.REMOVED, manual)


class BugSprintLog(models.Model):
    ADDED = 0
    REMOVED = 1
    ACTION_CHOICES = (
        (ADDED, 'Added'),
        (REMOVED, 'Removed'),
    )

    bug = models.ForeignKey(Bug, related_name='sprint_actions')
    sprint = models.ForeignKey(Sprint, related_name='bug_actions')
    action = models.PositiveSmallIntegerField(choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=datetime.now)
    manual = models.BooleanField()

    objects = BugSprintLogManager()

    class Meta:
        ordering = ('-timestamp',)

    def __unicode__(self):
        action = self.get_action_display().lower()
        action += ' to' if self.action == self.ADDED else ' from'
        return u'Bug %d %s Sprint %d' % (self.bug_id, action, self.sprint_id)


def extract_bug_kwargs(data):
    kwargs = data.copy()
    kwargs['assigned_to'] = '||'.join([kwargs['assigned_to']['name'],
                                       kwargs['assigned_to']['real_name']])
    if 'url' in kwargs:
        del kwargs['url']
    if 'whiteboard' in kwargs:
        scrum_data = parse_whiteboard(kwargs['whiteboard'])
        for key, val in scrum_data.iteritems():
            if val:
                kwargs['story_' + key] = val
    return kwargs


@transaction.commit_on_success
def store_bugs(bugs, sprint=None):
    bug_objs = []
    for bug in bugs:
        bug_objs.append(Bug.objects.update_or_create(bug)[0])
    if sprint:
        sprint.update_bugs([bug['id'] for bug in bugs])
    return bug_objs


class DummyBug:
    sprint = None
    sprint_id = None


@receiver(pre_save, sender=Bug)
def log_bug_actions(sender, instance, **kwargs):
    try:
        old_bug = Bug.objects.get(id=instance.id)
    except Bug.DoesNotExist:
        old_bug = DummyBug()
    if old_bug.sprint_id != instance.sprint_id:
        if old_bug.sprint:
            BugSprintLog.objects.removed_from_sprint(instance, old_bug.sprint,
                                                     old_bug.added_manually)
        if instance.sprint:
            BugSprintLog.objects.added_to_sprint(instance, instance.sprint,
                                                 instance.added_manually)


@receiver(pre_save, sender=Sprint)
def process_notes(sender, instance, **kwargs):
    if instance.notes:
        instance.notes_html = markdown(
            force_unicode(instance.notes),
            # http://packages.python.org/Markdown/extensions/index.html
            extensions=[
                'nl2br',
                'fenced_code',
                'tables',
                'smart_strong',
                'sane_lists',
            ],
            output_format='html5',
            safe_mode=True,
        )

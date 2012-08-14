from __future__ import absolute_import

import hashlib
import re
import zlib
from base64 import b64decode, b64encode
from collections import defaultdict
from datetime import date, datetime
from markdown import markdown
from operator import itemgetter

from django.conf import settings
from django.core.cache import cache
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models.query_utils import Q
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
    'resolution',
    'summary',
    'history',
    'whiteboard',
    'assigned_to',
    'priority',
    'product',
    'component',
    'blocks',
    'depends_on',
    'comments',
    'creation_time',
    'last_change_time',
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

    def needs_refresh(self):
        return (datetime.now() - self.date_cached).seconds > CACHE_BUGS_FOR

    def get_bugs(self, **kwargs):
        raise NotImplementedError

    def get_components(self):
        raise NotImplementedError

    def get_products(self):
        raise NotImplementedError

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


class Team(BugsListMixin, models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=50, validators=[validate_slug],
                            db_index=True, unique=True)

    def __unicode__(self):
        return self.name

    def get_bugs(self):
        """
        Get all bugs from the ready backlogs of the projects.
        :return: list of bugs
        """
        return Bug.objects.filter(project__team=self, sprint__isnull=True)

    @models.permalink
    def get_absolute_url(self):
        return 'scrum_team', [self.slug]

    @models.permalink
    def get_edit_url(self):
        return 'scrum_team_edit', [self.slug]


class DBBugsMixin(object):

    def _get_bugs(self, **kwargs):
        """Get the db associated bugs (sprint/ready backlog)"""
        self.scrum_only = kwargs.get('scrum_only', True)
        if kwargs.get('refresh', False):
            self.refresh_bugs_data()
        bugs = self.bugs.all()
        if self.scrum_only:
            num_bugs = bugs.count()
            bugs = bugs.filter(~Q(story_component='') |
                               ~Q(story_user__isnull='') |
                               Q(story_points__gt=0))
            self.num_no_data_bugs = num_bugs - bugs.count()
        return bugs


class Project(DBBugsMixin, BugsListMixin, models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=50, validators=[validate_slug],
                            db_index=True, unique=True)
    team = models.ForeignKey(Team, related_name='projects', null=True)

    _date_cached = None

    def __unicode__(self):
        return self.name

    @property
    def date_cached(self):
        if self._date_cached is None:
            # warm cache
            self.get_bugs()
        return self._date_cached if self._date_cached else datetime.now()

    def get_bz_search_url(self):
        return BugzillaURL(url=get_bz_url_for_buglist(self.bugs.all()))

    def refresh_bugs_data(self):
        bzurl = self.get_bz_search_url()
        bzurl.get_bugs(refresh=True)

    def get_bugs(self, **kwargs):
        bugs = self._get_bugs(**kwargs)
        bugs.filter(sprint__isnull=True)
        return bugs

    def get_backlog(self, **kwargs):
        """Get a unique set of bugs from all bz urls"""
        refresh = kwargs.get('refresh', False)
        self.scrum_only = kwargs.get('scrum_only', True)
        if refresh:
            self._clear_bugs_data_cache()
        backlog = self._get_url_items('bugs', **kwargs)
        return [bug for bug in backlog if (not bug.sprint and not bug.project)]

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

                if (self._date_cached is None or
                    (url.date_cached and url.date_cached < self._date_cached)):
                    self._date_cached = url.date_cached
                if item_name == 'bugs' and url.num_no_data_bugs:
                    self.num_no_data_bugs += url.num_no_data_bugs

            setattr(self, attr_name, list(items))
        return getattr(self, attr_name)

    @models.permalink
    def get_absolute_url(self):
        return 'scrum_project', [self.slug]

    @models.permalink
    def get_edit_url(self):
        return 'scrum_project_edit', [self.slug]

    def get_urls(self):
        return self.urls.all()

    def update_bugs(self, bugs):
        """
        Add and remove bugs to sync the list with what we receive.
        :param bug_ids: list of bugs or bug ids
        :return: None
        """
        to_add, to_remove = get_sync_bugs(self.bugs.all(), bugs)
        # saving individually to fire signals
        for bug in to_add:
            bug.project = self
            bug.save()
        for bug in to_remove:
            bug.project = None
            bug.save()


class Sprint(DBBugsMixin, BugsListMixin, models.Model):
    team = models.ForeignKey(Team, related_name='sprints')
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

    class Meta:
        get_latest_by = 'created_date'
        ordering = ['-start_date']
        unique_together = ('team', 'slug')

    def __unicode__(self):
        return u'{0} - {1}'.format(self.team.name, self.name)

    def is_active(self):
        return self.start_date <= date.today() <= self.end_date

    @property
    def date_cached(self):
        """
        Returns the datetime of the bug least recently synced from Bugzila.
        :return: datetime
        """
        try:
            return self.bugs.order_by('last_synced_time')[0].last_synced_time
        except IndexError:
            return datetime.now()

    def get_bugs(self, **kwargs):
        return self._get_bugs(**kwargs)

    def get_components(self):
        return self._get_bug_attr_values('component')

    def get_products(self):
        return self._get_bug_attr_values('product')

    def _get_bug_attr_values(self, attr):
        attr_values = {}
        for bug in self.get_bugs(scrum_only=False):
            attr_values[getattr(bug, attr)] = 0
        return attr_values.keys()

    @models.permalink
    def get_absolute_url(self):
        return 'scrum_sprint', (), {'slug': self.team.slug,
                                    'sslug': self.slug}

    @models.permalink
    def get_edit_url(self):
        return 'scrum_sprint_edit', (), {'slug': self.team.slug,
                                         'sslug': self.slug}

    def get_bz_search_url(self):
        bugs_all = self.bugs.all()
        if bugs_all:
            return BugzillaURL(url=get_bz_url_for_buglist(bugs_all))
        return EmptyBugzillaURL()

    def refresh_bugs_data(self):
        self._clear_bugs_data_cache()
        bzurl = self.get_bz_search_url()
        bzurl.get_bugs(refresh=True)

    def update_bugs(self, bugs):
        """
        Add and remove bugs to sync the list with what we receive.
        :param bugs: list of bugs or bug ids
        :return: None
        """
        to_add, to_remove = get_sync_bugs(self.bugs.all(), bugs)
        # saving individually to fire signals
        for bug in to_add:
            bug.sprint = self
            bug.save()
        for bug in to_remove:
            bug.sprint = None
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
        bugs_data = self.bugs_data_cache
        if bugs_data is None:
            bugs_data = self.get_bugs_data()
        return bugs_data


class EmptyBugzillaURL(object):
    def get_bugs(self, **kwargs):
        return []


class BugzillaURL(models.Model):
    url = models.URLField(verbose_name='Bugzilla URL', max_length=2048)
    project = models.ForeignKey(Project, null=True, blank=True,
                                related_name='urls')

    date_cached = None
    num_no_data_bugs = 0

    class Meta:
        ordering = ('id',)

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
                self._bugs = set(store_bugs(data['bugs']))
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
        defaults = clean_bug_data(data)
        bid = defaults.pop('id')
        bug, created = self.get_or_create(id=bid, defaults=defaults)
        if not created:
            bug.fill_from_data(defaults)
            bug.save()
        return bug, created


class Bug(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    history = CompressedJSONField()
    last_synced_time = models.DateTimeField(default=datetime.utcnow)
    product = models.CharField(max_length=200)
    component = models.CharField(max_length=200)
    assigned_to = models.CharField(max_length=200)
    status = models.CharField(max_length=20)
    resolution = models.CharField(max_length=20, blank=True)
    summary = models.CharField(max_length=500)
    priority = models.CharField(max_length=2, blank=True)
    whiteboard = models.CharField(max_length=200, blank=True)
    blocks = JSONField(blank=True)
    depends_on = JSONField(blank=True)
    comments = CompressedJSONField(blank=True)
    comments_count = models.PositiveSmallIntegerField(default=0)
    # not a URLField b/c don't want URL validation
    url = models.CharField(max_length=2048, blank=True)
    creation_time = models.DateTimeField()
    last_change_time = models.DateTimeField()
    story_user = models.CharField(max_length=50, blank=True)
    story_component = models.CharField(max_length=50, blank=True)
    story_points = models.PositiveSmallIntegerField(default=0)

    sprint = models.ForeignKey(Sprint, related_name='bugs', null=True,
                               on_delete=models.SET_NULL)
    project = models.ForeignKey(Project, related_name='bugs', null=True,
                                on_delete=models.SET_NULL)

    objects = BugManager()

    class Meta:
        ordering = ('id',)

    def __unicode__(self):
        return unicode(self.id)

    def fill_from_data(self, data):
        self.__dict__.update(data)
        self.last_synced_time = datetime.now()

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
                                phistory.append({'date': hdate,
                                                 'points': pts})
            self._points_history = phistory
        return self._points_history


class BugSprintLogManager(models.Manager):
    def _record_action(self, bug, sprint, action):
        self.create(bug=bug, sprint=sprint, action=action)

    def added_to_sprint(self, bug, sprint):
        self._record_action(bug, sprint, BugSprintLog.ADDED)

    def removed_from_sprint(self, bug, sprint):
        self._record_action(bug, sprint, BugSprintLog.REMOVED)


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

    objects = BugSprintLogManager()

    class Meta:
        ordering = ('-timestamp',)

    def __unicode__(self):
        action = self.get_action_display().lower()
        action += ' to' if self.action == self.ADDED else ' from'
        return u'Bug %d %s Sprint %d' % (self.bug_id, action, self.sprint_id)


_bug_data_cleaners = {
    'id': int,
    'last_change_time': dateutil.parser.parse,
    'creation_time': dateutil.parser.parse,
    'assigned_to': lambda x: '||'.join([x['name'],
                                        x.get('real_name', x['name'])]),
    # The bzapi docs are wrong and say that 'depends_on' is a list of integers
    # when in fact it could be a single string, or a list of strings.
    # 'blocks' is the same type but is always a list of strings.
    'depends_on': list,
}


def clean_bug_data(data):
    """
    Clean and prepare the data we get from Bugzilla for the db.

    :param data: dict of raw Bugzilla API data for a single bug.
    :return: dict of cleaned data for a single bug ready for the db.
    """
    kwargs = data.copy()
    for key in _bug_data_cleaners:
        if key in kwargs:
            kwargs[key] = _bug_data_cleaners[key](kwargs[key])

    if 'whiteboard' in kwargs:
        scrum_data = parse_whiteboard(kwargs['whiteboard'])
        kwargs.update(dict(('story_' + k, v) for k, v in scrum_data.items()
                           if v))
    if 'comments' in kwargs:
        kwargs['comments_count'] = len(kwargs['comments'])

    return kwargs


@transaction.commit_on_success
def store_bugs(bugs):
    bug_objs = []
    for bug in bugs:
        bug_objs.append(Bug.objects.update_or_create(bug)[0])
    return bug_objs


def get_sync_bugs(current_bugs, new_bugs):
    """
    Take two lists of bugs and return two lists of which to add and remove.
    :param current_bugs: Iterator of current bugs
    :param new_bugs: Iterator of new bugs
    :return: tuple (bugs to add, bugs to remove)
    """
    if new_bugs:
        if isinstance(list(new_bugs)[0], Bug):
            new_bugs = set(new_bugs)
        else:
            new_bugs = set(Bug.objects.filter(id__in=new_bugs))
    else:
        new_bugs = set()
    current_bugs = set(current_bugs)
    to_add = new_bugs - current_bugs
    to_remove = current_bugs - new_bugs
    return to_add, to_remove


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
            BugSprintLog.objects.removed_from_sprint(instance, old_bug.sprint)
        if instance.sprint:
            BugSprintLog.objects.added_to_sprint(instance, instance.sprint)


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

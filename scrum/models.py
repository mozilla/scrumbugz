from __future__ import absolute_import

import hashlib
import logging
import operator
from django.db.models.query import QuerySet
import re
import zlib
from base64 import b64decode, b64encode
from collections import defaultdict
from datetime import date, timedelta
from operator import itemgetter

from django.conf import settings
from django.core.cache import cache
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models.query_utils import Q
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils.encoding import force_unicode
from django.utils.timezone import now

import dateutil.parser
from jsonfield import JSONField
from markdown import markdown
from model_utils.managers import PassThroughManager

from bugzilla.api import BUG_OPEN_STATUSES, bugzilla, is_closed
from scrum.utils import (date_to_js, date_range, get_bz_url_for_bug_ids,
                         get_story_data, parse_bz_url, parse_whiteboard)


log = logging.getLogger(__name__)
ALL_COMPONENTS = '__ALL__'


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
        return (now() - self.date_cached).seconds > CACHE_BUGS_FOR

    def get_bugs(self, **kwargs):
        raise NotImplementedError

    def get_components(self):
        raise NotImplementedError

    def get_products(self):
        raise NotImplementedError

    def _get_bugs_data(self):
        return self.get_bugs().get_aggregate_data()

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
        return self.get_bugs().get_graph_data()


class DBBugsMixin(object):

    def _get_bugs(self, **kwargs):
        """Get the db associated bugs (sprint/ready backlog)"""
        self.scrum_only = kwargs.get('scrum_only', True)
        bugs = kwargs.get('bugs')
        if bugs is None:
            bugs = self.bugs.all()
        if 'bug_filters' in kwargs:
            bugs = bugs.filter(**kwargs['bug_filters'])
        if self.scrum_only:
            num_bugs = bugs.count()
            bugs = bugs.scrum_only()
            self.num_no_data_bugs = num_bugs - bugs.count()
        if kwargs.get('refresh', False):
            self.refresh_bugs_data(bugs)
        return bugs

    def refresh_bugs_data(self, bugs=None):
        from scrum.tasks import update_bug_chunks
        update_bug_chunks(bugs if bugs is not None else self.bugs.all())

    def get_bugs(self, **kwargs):
        kwargs['bug_filters'] = {'sprint__isnull': True}
        return self._get_bugs(**kwargs)

    def _force_bug_qs(self, blist):
        if isinstance(blist, list):
            blist = Bug.objects.filter(id__in=blist).only('id')
        return blist

    def log_bugs_add(self, bugs):
        pass

    def log_bugs_remove(self, bugs):
        pass

    def update_bugs(self, add=None, remove=None):
        """
        Add and remove bugs to sync the list with what we receive.
        :param add, remove: list of bug ids or bugs queryset
        :return: None
        """
        if remove:
            for bug in self._force_bug_qs(remove):
                try:
                    self.bugs.remove(bug)
                    self.log_bugs_remove([bug])
                except self.DoesNotExist:
                    pass
        if add:
            qs = self._force_bug_qs(add)
            self.log_bugs_add(qs)
            self.bugs.add(*qs)


class Team(DBBugsMixin, BugsListMixin, models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=50, validators=[validate_slug],
                            db_index=True, unique=True)

    class Meta:
        ordering = ('name',)

    def get_bugs(self, **kwargs):
        """
        Get all bugs from the ready backlogs of the projects.
        :return: bugs queryset
        """
        kwargs['bugs'] = Bug.objects.filter(project__team=self,
                                            sprint__isnull=True).open()
        return self._get_bugs(**kwargs)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return 'scrum_team', [self.slug]

    @models.permalink
    def get_edit_url(self):
        return 'scrum_team_edit', [self.slug]


class Project(DBBugsMixin, BugsListMixin, models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=50, validators=[validate_slug],
                            db_index=True, unique=True)
    team = models.ForeignKey(Team, related_name='projects', null=True)

    _date_cached = None

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    @property
    def date_cached(self):
        if self._date_cached is None:
            # warm cache
            self.get_bugs()
        return self._date_cached if self._date_cached else now()

    def get_backlog(self, **kwargs):
        """Get a unique set of bugs from all bz urls"""

        self.scrum_only = kwargs.get('scrum_only', True)
        bugs = Bug.objects.open().filter(sprint__isnull=True,
                                         project__isnull=True)
        bugs = bugs.by_products(self.get_products())
        if self.scrum_only:
            bugs = bugs.scrum_only()
        return bugs

    def get_products(self):
        return get_bzproducts_dict(self.products.all())

    def get_components(self):
        all_comps = set(reduce(operator.add, self.get_products().values(), []))
        return list(comp for comp in all_comps if comp != ALL_COMPONENTS)

    @models.permalink
    def get_absolute_url(self):
        return 'scrum_project', [self.slug]

    @models.permalink
    def get_edit_url(self):
        return 'scrum_project_edit', [self.slug]


class BZProductManager(models.Manager):
    _full_list_cache_key = 'bzproducts-full-list'

    def full_list(self):
        """
        Despite the method name, returns a dict of all products (keys) and
        components (values list) that all projects have specified.
        :return: dict
        """
        data = cache.get(self._full_list_cache_key)
        if not data:
            data = get_bzproducts_dict(self.all())
            cache.set(self._full_list_cache_key, data, 60 * 60 * 24)
        return data

    def _reset_full_list(self):
        cache.delete(self._full_list_cache_key)


class BZProduct(models.Model):
    name = models.CharField(max_length=200)
    component = models.CharField(max_length=200)
    project = models.ForeignKey(Project, related_name='products')

    objects = BZProductManager()


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
    created_date = models.DateTimeField(editable=False, default=now)
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
            return (self.bugs.order_by('last_synced_time')
                    .only('last_synced_time')[0].last_synced_time)
        except IndexError:
            return now()

    def get_bugs(self, **kwargs):
        return self._get_bugs(**kwargs)

    def get_components(self):
        return self._get_bug_attr_values('component')

    def get_products(self):
        return self._get_bug_attr_values('product')

    def _get_bug_attr_values(self, attr):
        attr_values = {}
        for bug in self.get_bugs(scrum_only=False).only(attr):
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

    def refresh_bugs_data(self, bugs=None):
        self._clear_bugs_data_cache()
        super(Sprint, self).refresh_bugs_data(bugs)

    def get_burndown(self):
        """Return a list of total point values per day of sprint"""
        today = now().date()
        sdate = self.start_date
        edate = self.end_date if self.end_date < today else today
        if sdate > today:
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

    def log_bugs_add(self, bugs):
        for bug in bugs:
            if bug.sprint:
                BugSprintLog.objects.removed_from_sprint(bug, bug.sprint)
            BugSprintLog.objects.added_to_sprint(bug, self)

    def log_bugs_remove(self, bugs):
        for bug in bugs:
            BugSprintLog.objects.removed_from_sprint(bug, self)


class BugzillaURL(models.Model):
    url = models.URLField(verbose_name='Bugzilla URL', max_length=2048)
    project = models.ForeignKey(Project, null=True, blank=True,
                                related_name='urls')
    # default in the past
    date_synced = models.DateTimeField(default=now() - timedelta(days=30))
    one_time = models.BooleanField(default=False)

    date_cached = None
    num_no_data_bugs = 0

    class Meta:
        ordering = ('id',)

    def _get_bz_args(self):
        """Return a dict of the arguments from the bz_url"""
        return parse_bz_url(self.url)

    def _clear_cache(self):
        try:
            delattr(self, '_bugs')
        except AttributeError:
            pass
        cache.delete(self._bugs_cache_key)

    @property
    def _bugs_cache_key(self):
        """
        sha1 digest of the url for use as the cache key.
        :return: str
        """
        return hashlib.sha1(self.url).hexdigest()

    def get_bugs(self, **kwargs):
        """
        Do the actual work of getting bugs from the BZ API
        :return: set
        """
        bugs = {}
        try:
            args = self._get_bz_args()
            args = dict((k.encode('utf-8'), v) for k, v in
                        args.iterlists())
            bzkwargs = {}
            if 'bug_id' in args:
                bzkwargs['ids'] = [int(bid) for bid in
                                   args['bug_id'][0].split(',')]
            else:
                for item in ['product', 'component']:
                    items = args.get(item)
                    if items:
                        bzkwargs[item] = items
            if bzkwargs:
                bzkwargs.update(kwargs)
                bugs = bugzilla.get_bugs(**bzkwargs)
                bugs['date_received'] = now()
        except Exception:
            log.exception('Problem fetching bugs from %s', self.url)
            raise BZError("Couldn't retrieve bugs from Bugzilla")
        if self.id and not self.one_time:
            self.date_synced = now()
            self.save()
        return set(store_bugs(bugs))

    def get_products(self):
        """Return a set of the products in the search url"""
        return set(self._get_bz_args().getlist('product'))

    def get_components(self):
        """Return a set of the components in the search url"""
        return set(self._get_bz_args().getlist('component'))

    def get_whiteboard(self):
        return self._get_bz_args().get('status_whiteboard')


class BugQuerySet(QuerySet):
    def sync_bugs(self):
        """
        Refresh the data for all matched bugs from Bugzilla.
        """
        from scrum.tasks import update_bug_chunks
        update_bug_chunks(self.only('id'))

    def scrum_only(self):
        """
        Only include bugs that have some data in the `story_*` fields.
        :return: QuerySet
        """
        return self.filter(Q(whiteboard__contains='u=') |
                           Q(whiteboard__contains='c=') |
                           Q(whiteboard__contains='p=') |
                           Q(whiteboard__contains='s='))

    def open(self):
        """
        Filter out closed bugs.
        :return: QuerySet
        """
        return self.filter(status__in=BUG_OPEN_STATUSES)

    def by_products(self, products):
        """
        Filter the bugs based on a dict of products and components like the
        one returned by `Project.get_products()`.
        :param products: dict
        :return: QuerySet
        """
        # empty products dict should return no bugs
        if not products:
            return self.filter(product='')
        qobjs = []
        for prod, comps in products.items():
            kwargs = {'product': prod}
            if comps and ALL_COMPONENTS not in comps:
                if len(comps) == 1:
                    kwargs['component'] = comps[0]
                else:
                    kwargs['component__in'] = comps
            qobjs.append(Q(**kwargs))
        return self.filter(reduce(operator.or_, qobjs))

    def get_bz_search_url(self):
        """
        Return a url for the list of bugs in this QS.
        :return: str
        """
        return get_bz_url_for_bug_ids(self.all().values_list('id', flat=True))

    def get_blocked(self):
        """
        Return a list of bug IDs from this QS that have open blocking bugs.
        """
        blocker_to_bug = defaultdict(list)
        for bug in self.only('id', 'depends_on'):
            for dep_id in bug.depends_on:
                blocker_to_bug[dep_id].append(bug.id)
        open_blockers = Bug.objects.filter(id__in=blocker_to_bug.keys()) \
                           .open()
        open_blocker = dict((b.id, b) for b in open_blockers)
        all_blocked = defaultdict(list)
        for blocker, blocked in blocker_to_bug.iteritems():
            if blocker in open_blocker:
                for bid in blocked:
                    all_blocked[bid].append(open_blocker[blocker])
        return all_blocked

    def get_flagged(self):
        """
        Return a list of bug ids of bugs with flags
        """
        flags = []
        for bug in self.open():
            if bug.bucketed_flags:
                flags.append(bug.id)
        return flags

    def get_aggregate_data(self):
        bugs = self.all()
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
                data['components'][bug.real_component] += bug.story_points
                data['status'][bug.status] += bug.story_points
                data['basic_status'][bug.basic_status] += bug.story_points
                data['total_points'] += bug.story_points
            else:
                data['scoreless_bugs'] += 1
        data['points_remaining'] = (data['total_points'] -
                                    data['basic_status']['closed'])
        return data

    def get_graph_data(self):
        data = self.get_aggregate_data()
        for item in ['users', 'components', 'status', 'basic_status']:
            data[item] = [{'label': k, 'data': v} for k, v in
                          sorted(data[item].iteritems(), key=itemgetter(1),
                                 reverse=True)]
        return data


class BugManager(PassThroughManager):
    use_for_related_fields = True

    def get_query_set(self):
        return BugQuerySet(self.model, using=self._db)

    def update_or_create(self, data):
        """
        Create or update a bug from the data returned from Bugzilla.
        :param data: dict of bug data from the bugzilla api.
        :return: Bug instance, boolean created.
        """
        defaults = data.copy()
        bid = defaults.pop('id')
        bug, created = self.get_or_create(id=bid, defaults=defaults)
        if not created:
            bug.fill_from_data(defaults)
            bug.save()
        log.info('updated bug %s', bug.id)
        cache.set('bug:updated:%s' % bug.id, True, 35)
        return bug, created


class Bug(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    history = CompressedJSONField(blank=True)
    last_synced_time = models.DateTimeField(default=now)
    product = models.CharField(max_length=200)
    component = models.CharField(max_length=200)
    assigned_to = models.CharField(max_length=500)
    status = models.CharField(max_length=20)
    resolution = models.CharField(max_length=20, blank=True)
    summary = models.CharField(max_length=500)
    priority = models.CharField(max_length=2, blank=True)
    whiteboard = models.CharField(max_length=2048, blank=True)
    blocks = JSONField(blank=True)
    depends_on = JSONField(blank=True)
    flags = CompressedJSONField(blank=True)
    attachments = CompressedJSONField(blank=True)
    comments_count = models.PositiveSmallIntegerField(default=0)
    creation_time = models.DateTimeField(default=now)
    last_change_time = models.DateTimeField(default=now)
    severity = models.CharField(max_length=20, blank=True)
    target_milestone = models.CharField(max_length=20, blank=True)
    story_user = models.CharField(max_length=50, blank=True)
    story_component = models.CharField(max_length=50, blank=True)
    story_points = models.PositiveSmallIntegerField(default=0)

    sprint = models.ForeignKey(Sprint, related_name='bugs', null=True,
                               on_delete=models.SET_NULL)
    project = models.ForeignKey(Project, related_name='bugs', null=True,
                                on_delete=models.SET_NULL)

    objects = BugManager()
    flag_status_names = {
        '?': 'question',
        '+': 'plus',
        '-': 'minus'
    }

    class Meta:
        ordering = ('id',)

    def __unicode__(self):
        return unicode(self.id)

    def projects_from_product(self):
        prodcomps = BZProduct.objects.filter(
            name=self.product,
            component__in=[self.component, ALL_COMPONENTS],
        )
        return list(set(pc.project for pc in prodcomps))

    def fill_from_data(self, data):
        for attr_name, value in data.items():
            setattr(self, attr_name, value)
        self.last_synced_time = now()

    def refresh_from_bugzilla(self):
        data = bugzilla.get_bugs(ids=[self.id]).get('bugs')
        self.fill_from_data(data[0])

    @models.permalink
    def get_absolute_url(self):
        return 'scrum_bug', [self.pk]

    def get_bugzilla_url(self):
        return '%sid=%s' % (settings.BUGZILLA_SHOW_URL, self.id)

    def get_bugzilla_attachment_url(self, attachment_id):
        if attachment_id == None:
            return None
        return '%sid=%s' % (settings.BUGZILLA_ATTACHMENT_URL, attachment_id)

    def is_closed(self):
        return is_closed(self.status)

    def is_assigned(self):
        return self.assigned_to != 'nobody@mozilla.org'

    def points_for_date(self, date):
        cpoints = self.story_points
        for h in self.points_history:
            if date < h['date']:
                return cpoints
            cpoints = h['points']
        return cpoints

    @property
    def assigned_name(self):
        # catch old bugs for a bit
        # TODO remove this later.
        if '||' in self.assigned_to:
            return self.assigned_to.split('||', 1)[0]
        return self.assigned_to.split('@', 1)[0]

    @property
    def assigned_full(self):
        # catch old bugs for a bit
        # TODO remove this later.
        if '||' in self.assigned_to:
            return self.assigned_to.split('||', 1)[1]
        return self.assigned_to

    @property
    def basic_status(self):
        if self.is_closed():
            status = 'closed'
        else:
            status = 'assigned' if self.is_assigned() else 'open'
        return status

    @property
    def scrum_data(self):
        data = get_story_data(self.whiteboard)
        if not data.get('component', None):
            data['component'] = self.component
        return data

    @property
    def real_component(self):
        return self.story_component or self.component

    @property
    def has_scrum_data(self):
        return bool('u=' in self.whiteboard or
                    'c=' in self.whiteboard or
                    'p=' in self.whiteboard or
                    's=' in self.whiteboard)

    def _bucket_flag(self, f):
        name = f.get('name', None)
        if not name:
            return (None,)

        who = f.get('requestee', f.get('setter', None))
        mod_date = f.get('modification_date', None)
        status = f.get('status', None)

        return (name, {'who': who, 'when': mod_date, 'status': status })

    @property
    def bucketed_flags(self):
        # do we have cached values?
        if hasattr(self, '_bucketed_flags'):
            return self._bucketed_flags

        bf = defaultdict(list)

        # filter the bug flags and put them in named buckets
        for f in self.flags:

            flag_name, flag_data = self._bucket_flag(f)
            if flag_name != None:
                bf[flag_name].append(flag_data)

        # add in the flags from attachments
        for a in self.attachments:

            # if is_obsolete is True, or is_obsolete field doesn't exist,
            # skip this attachment
            if a.get('is_obsolete', True):
                continue

            # put the attachment flags into the buckets
            for f in a.get('flags', []):

                flag_name, flag_data = self._bucket_flag(f)
                if flag_name == None:
                    continue

                ref_id = a.get('id', None)
                ref_name = a.get('file_name', None)
                ref_link = self.get_bugzilla_attachment_url(ref_id)
                flag_data.update({
                    'ref_id': ref_id,
                    'ref_name': ref_name,
                    'ref_link': ref_link})

                bf[flag_name].append(flag_data)

        self._bucketed_flags = bf
        return self._bucketed_flags

    def _flag_status_name(self, status):
        return self.flag_status_names.get(status, 'none')

    def _bucket_flag_status(self, flag, fs):
        flag_name = flag.get('name', None)
        if not flag_name:
            return {}

        status_name = self._flag_status_name(flag.get('status', None))
        if fs.get(flag_name, None) is None or status_name == fs[flag_name]:
            return {flag_name: status_name}
        else:
            return {flag_name: 'mixed'}

    @property
    def flags_status(self):
        # do we have cached values?
        if hasattr(self, '_flags_status'):
            return self._flags_status

        fs = {}

        # update the status for each flag bucket
        for f in self.flags:
            fs.update(self._bucket_flag_status(f, fs))

        # go through attachment flags too
        for a in self.attachments:
            # if is_obsolete is True, or is_obsolete field doesn't exist,
            # skip this attachment
            if a.get('is_obsolete', True):
                continue

            for f in a.get('flags', []):
                fs.update(self._bucket_flag_status(f, fs))

        self._flags_status = fs
        return self._flags_status

    @property
    def points_history(self):
        if not hasattr(self, '_points_history'):
            phistory = []
            cpoints = 0
            closed = False
            for h in self.history:
                # TODO remove 'change_time' when all bugs are updated
                hdate = dateutil.parser.parse(h.get('when') or
                                              h.get('change_time')).date()
                for change in h['changes']:
                    fn = change['field_name']
                    # TODO remove 'status' when all bugs are updated
                    if fn == 'bug_status' or fn == 'status':
                        now_closed = is_closed(change['added'])
                        if closed != now_closed:
                            pts = 0 if now_closed else cpoints
                            phistory.append({
                                'date': hdate,
                                'points': pts,
                                })
                            closed = now_closed
                    elif fn == 'status_whiteboard':
                        pts = get_story_data(change['added'])['points']
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
        log.debug('Adding %s to %s', bug, sprint)
        self._record_action(bug, sprint, BugSprintLog.ADDED)

    def removed_from_sprint(self, bug, sprint):
        log.debug('Removing %s from %s', bug, sprint)
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
    timestamp = models.DateTimeField(default=now)

    objects = BugSprintLogManager()

    class Meta:
        ordering = ('-timestamp',)

    def __unicode__(self):
        action = self.get_action_display().lower()
        action += ' to' if self.action == self.ADDED else ' from'
        return u'Bug %d %s Sprint %d' % (self.bug_id, action, self.sprint_id)


@transaction.commit_on_success
def store_bugs(bugs):
    bug_objs = []
    update_sprints = set()
    for bug in bugs.get('bugs', []):
        bug_obj = Bug.objects.update_or_create(bug)[0]
        bug_objs.append(bug_obj)
        if bug_obj.sprint:
            update_sprints.add(bug_obj.sprint.id)
    if update_sprints:
        from scrum.tasks import update_sprint_data
        update_sprint_data.delay(list(update_sprints))
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


def get_bzproducts_dict(qs):
    prods = {}
    for prod in qs:
        if prod.name not in prods or prod.component == ALL_COMPONENTS:
            prods[prod.name] = []
        if not (ALL_COMPONENTS in prods[prod.name] or
                prod.component in prods[prod.name]):
            prods[prod.name].append(prod.component)
    return prods


@receiver(pre_save, sender=Bug)
def update_scrum_data(sender, instance, **kwargs):
    for k, v in instance.scrum_data.items():
        setattr(instance, 'story_' + k, v)


TM_RE = re.compile(r'\d{4}-\d{2}-\d{2}$')


@receiver(pre_save, sender=Bug)
def move_to_sprint(sender, instance, **kwargs):
    if not instance.has_scrum_data:
        return
    wb_data = parse_whiteboard(instance.whiteboard)
    newsprint = None
    if 's' in wb_data:
        newsprint = wb_data['s']
    elif instance.target_milestone and instance.target_milestone != '---' \
            and TM_RE.match(instance.target_milestone):
        newsprint = instance.target_milestone

    if newsprint:
        if instance.sprint and newsprint == instance.sprint.slug:
            # already in the sprint
            return

        newsprint_obj = None
        proj = None
        new_projs = instance.projects_from_product()
        for proj in new_projs:
            try:
                newsprint_obj = Sprint.objects.get(team=proj.team,
                                                   slug=newsprint)
                break
            except Sprint.DoesNotExist:
                continue

        if not newsprint_obj:
            return

        if instance.sprint:
            BugSprintLog.objects.removed_from_sprint(instance,
                                                     instance.sprint)
        instance.sprint = newsprint_obj
        instance.project = proj
        BugSprintLog.objects.added_to_sprint(instance, newsprint_obj)


@receiver(pre_save, sender=Sprint)
def process_notes(sender, instance, **kwargs):
    if instance.notes:
        instance.notes_html = markdown(
            force_unicode(instance.notes),
            extensions=settings.MARKDOWN_EXTENSIONS,
            output_format='html5',
            safe_mode=True,
        )


@receiver(post_save, sender=BZProduct)
def fetch_product_bugs(sender, instance, **kwargs):
    # avoid circular imports
    from .tasks import update_product
    BZProduct.objects._reset_full_list()
    args = [instance.name]
    if instance.component != ALL_COMPONENTS:
        args.append(instance.component)
    update_product.delay(*args)

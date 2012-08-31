from __future__ import absolute_import

from copy import deepcopy
from datetime import date, timedelta, datetime
from email.parser import Parser

from mock import Mock, patch
from nose.tools import eq_, ok_

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import simplejson as json

from scrum import cron as scrum_cron
from scrum import bugmail as scrum_email
from scrum import models as scrum_models
from scrum.forms import BZURLForm, CreateProjectForm, SprintBugsForm
from scrum.models import BugSprintLog, BugzillaURL, Bug, Project, Sprint


scrum_models.BZAPI = Mock()
TEST_DATA = settings.PROJECT_DIR.child('scrum', 'test_data')
BUG_DATA_FILE = TEST_DATA.child('bugzilla_data.json')
BUGMAIL_FILES = (
    TEST_DATA.child('bugmail.txt'),
    TEST_DATA.child('bugmail2.txt'),
)

with open(BUG_DATA_FILE) as bdf:
    BUG_DATA = json.load(bdf)

GOOD_BZ_URL = BUG_DATA['bz_url']

# have to deepcopy to avoid cross-test-pollution
scrum_models.BZAPI.bug.get.side_effect = lambda *x, **y: deepcopy(BUG_DATA)


def get_messages_mock(delete=True):
    msgs = []
    for fn in BUGMAIL_FILES:
        with open(fn) as bmf:
            msgs.append(Parser().parse(bmf))
    return msgs


scrum_email.get_messages = Mock()
scrum_email.get_messages.side_effect = get_messages_mock


class TestCron(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.p = Project.objects.get(pk=1)

    def test_default_sync_date_urls_synced(self):
        """Test that BugzillaURL objects with NULL sync dates are synced."""
        BugzillaURL.objects.create(url=GOOD_BZ_URL, project=self.p)
        scrum_cron.sync_backlogs()
        eq_(self.p.backlog_bugs.count(), 20)

    def test_recently_synced_urls_not_synced(self):
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        url = BugzillaURL.objects.create(url=GOOD_BZ_URL, date_synced=hour_ago)
        scrum_cron.sync_backlogs()
        url = BugzillaURL.objects.get(id=url.id)
        eq_(url.date_synced, hour_ago)

    def test_one_time_urls_deleted(self):
        url = BugzillaURL.objects.create(url=GOOD_BZ_URL, one_time=True)
        scrum_cron.sync_backlogs()
        with self.assertRaises(BugzillaURL.DoesNotExist):
            BugzillaURL.objects.get(id=url.id)


class TestEmail(TestCase):
    def test_is_bugmail(self):
        m = scrum_email.get_messages()[0]
        ok_(scrum_email.is_bugmail(m))
        del m['x-bugzilla-type']
        ok_(not scrum_email.is_bugmail(m))

    def test_get_bugmails(self):
        good_data = [760693, 760694]
        eq_(good_data, sorted(scrum_email.get_bugmails().keys()))


class TestBug(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        cache.clear()
        self.s = Sprint.objects.get(slug='2.2')
        self.p = Project.objects.get(pk=1)
        self.url = Project.objects.get(pk=1)
        scrum_cron.sync_backlogs()

    @patch.object(Bug, 'points_history')
    def test_points_for_date_default(self, mock_bug):
        """ should default to points in whiteboard """
        bugs = self.p.get_backlog()
        b = bugs[0]
        eq_(b.story_points, b.points_for_date(date.today()))

    def test_db_bugs(self):
        bugs = self.p.get_backlog()
        compare_fields = [
            'summary',
            'status',
            'whiteboard',
            'product',
            'component',
        ]
        for bug in bugs:
            cbug = Bug.objects.get(id=bug.id)
            for fieldname in compare_fields:
                self.assertEqual(getattr(bug, fieldname),
                                 getattr(cbug, fieldname))

    def test_depends_on(self):
        """
        Tests a bug found where the BZ REST API returns a single string if
        there is one value, but a list if more than one.
        """
        b = Bug.objects.get(id=775147)
        eq_(b.depends_on, [776759])
        b = Bug.objects.get(id=665747)
        eq_(b.depends_on, [766748, 766749, 766750])


class TestBugzillaURL(TestCase):
    def setUp(self):
        self.bzurl = ('https://bugzilla.mozilla.org/buglist.cgi?'
                      'product=Mozilla%20Developer%20Network')

    def test_bz_args(self):
        """
        args should be added for bug status and whiteboard
        :return:
        """
        statuses = set(['UNCONFIRMED', 'ASSIGNED', 'REOPENED', 'NEW'])
        url = BugzillaURL(url=self.bzurl)
        args = url._get_bz_args()
        self.assertSetEqual(set(args.getlist('bug_status')), statuses)
        eq_(args['status_whiteboard'], 'u= c= p=')

    def test_url_args_override_defaults(self):
        """
        You should still be able to specify your own statuses and whiteboard.
        """
        url = BugzillaURL(url=self.bzurl + ';bug_status=CLOSED'
                                           ';status_whiteboard=u%3Dthedude')
        args = url._get_bz_args()
        eq_(args['bug_status'], 'CLOSED')
        eq_(args['status_whiteboard'], 'u=thedude')

    def test_url_args_not_modified(self):
        """
        Setting the proper arguments turns off automatic args addition.
        """
        url = BugzillaURL(url=self.bzurl)
        args = url._get_bz_args(open_only=False, scrum_only=False)
        ok_('bug_status' not in args)
        ok_('status_whiteboard' not in args)


class TestProject(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        cache.clear()
        self.s = Sprint.objects.get(slug='2.2')
        self.t = self.s.team
        self.p = Project.objects.get(pk=1)

    def test_refreshing_bugs_not_remove_from_sprint(self):
        """
        Refreshing bugs from Bugzilla does not remove them from a sprint.
        """
        bugs = self.s.get_bugs(scrum_only=False)
        self.assertEqual(Bug.objects.filter(sprint=self.s).count(),
                         len(bugs)
        )
        self.s.get_bugs(refresh=True)
        self.assertEqual(Bug.objects.filter(sprint=self.s).count(),
                         len(bugs))

    def test_adding_bzurl_adds_backlog_bugs(self):
        """Adding a url to a project should populate the backlog."""
        # should have created and loaded bugs when fixture loaded
        self.p.backlog_bugs.clear()
        eq_(self.p.backlog_bugs.count(), 0)
        # now this should update the existing bugs w/ the backlog
        BugzillaURL.objects.create(url=GOOD_BZ_URL, project=self.p)
        scrum_cron.sync_backlogs()
        eq_(self.p.backlog_bugs.count(), 20)


class TestSprint(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        cache.clear()
        self.s = Sprint.objects.get(slug='2.2')
        self.p = Project.objects.get(pk=1)
        scrum_cron.sync_backlogs()

    def test_sprint_creation(self):
        User.objects.create_superuser('admin', 'admin@admin.com', 'admin')
        self.client.login(username='admin', password='admin')
        t = self.s.team
        fdata = {
            'name': '1.3.37',
            'slug': '1.3.37',
            'start_date': '2012-01-01',
            'end_date': '2012-01-15',
        }
        url = reverse('scrum_sprint_new', args=[t.slug])
        resp = self.client.post(url, fdata, follow=True)
        self.assertRedirects(resp, reverse('scrum_sprint_bugs', kwargs={
            'slug': t.slug,
            'sslug': '1.3.37',
        }))

    def test_get_products(self):
        products = self.p.get_products()
        eq_(2, len(products))
        ok_('mozilla.org' in products)

    def test_get_components(self):
        components = self.p.get_components()
        eq_(11, len(components))
        ok_('Website' in components)

    def test_sprint_bug_logging(self):
        bzurl = BugzillaURL.objects.create(
            url='http://example.com/?stuff=whatnot'
        )
        bugs = bzurl.get_bugs()
        bug_ids = set(int(bug.id) for bug in bugs)
        cbug_ids = set(bug.id for bug in Bug.objects.all())
        self.assertSetEqual(bug_ids, cbug_ids)
        self.assertEqual(0, BugSprintLog.objects.count())
        bugs = self.p.get_backlog(scrum_only=False)
        self.s.update_bugs(bugs)
        self.assertEqual(len(bugs), BugSprintLog.objects.count())
        action = Bug.objects.all()[0].sprint_actions.all()[0].action
        self.assertEqual(action, BugSprintLog.ADDED)

    def test_sprint_bug_move_logging(self):
        self.s.update_bugs(self.p.get_backlog())
        newsprint = Sprint.objects.create(
            name='New Sprint',
            slug='newsprint',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            team=self.s.team
        )
        bug = Bug.objects.get(id=665747)
        bug.sprint = None
        bug.save()
        self.assertEqual(BugSprintLog.REMOVED,
                         bug.sprint_actions.all()[0].action)
        bug.sprint = newsprint
        bug.save()
        self.assertEqual(BugSprintLog.ADDED,
                         bug.sprint_actions.all()[0].action)

    def test_sprint_bug_steal_logging(self):
        self.s.update_bugs(self.p.get_backlog(scrum_only=False))
        newsprint = Sprint.objects.create(
            name='New Sprint',
            slug='newsprint',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            team=self.s.team
        )
        # closed bug should not be associated
        bug = Bug.objects.get(id=671774)
        self.assertEqual(bug.sprint, None)
        bug = Bug.objects.get(id=665747)
        self.assertEqual(bug.sprint, self.s)
        bug.sprint = newsprint
        bug.save()
        self.assertEqual(bug.sprint_actions.count(), 3)
        self.assertEqual(BugSprintLog.REMOVED,
                         bug.sprint_actions.all()[1].action)
        self.assertEqual(BugSprintLog.ADDED,
                         bug.sprint_actions.all()[0].action)

    def test_backlog_bug_sync(self):
        self.s.update_bugs(self.p.get_backlog())
        self.s.bugs.remove(Bug.objects.get(id=665747))
        self.assertEqual(self.s.bugs.count(), 3)
        new_bug_ids = [665747, 770965, 775147]
        self.s.update_bugs(new_bug_ids)
        self.assertEqual(self.s.bugs.count(), 3)
        all_bl_bug_ids = self.s.bugs.values_list('id', flat=True)
        self.assertSetEqual(set(all_bl_bug_ids), set(new_bug_ids))
        # the process of syncing did not remove bugs unnecessarily
        self.assertEqual(self.s.bug_actions.filter(
            bug_id__in=[770965, 775147],
            action=BugSprintLog.REMOVED,
        ).count(), 0)
        # the bug was added back, thus the 2 ADDED actions.
        self.assertEqual(self.s.bug_actions.filter(
            bug_id=665747,
            action=BugSprintLog.ADDED
        ).count(), 2)

    def test_sprint_bug_management(self):
        self.s.update_bugs(self.p.get_backlog())
        self.s.bugs.remove(Bug.objects.get(id=665747))
        self.assertEqual(self.s.bugs.count(), 3)
        new_bug_ids = [665747, 770965, 775147]
        form = SprintBugsForm(instance=self.s, data={
            'new_bugs': ','.join(str(bid) for bid in new_bug_ids),
        })
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(self.s.bugs.count(), 3)
        all_bl_bug_ids = self.s.bugs.values_list('id', flat=True)
        self.assertSetEqual(set(all_bl_bug_ids), set(new_bug_ids))

    def test_sprint_bugs_form_validation(self):
        # non digit
        form = SprintBugsForm(instance=self.s, data={
            'new_bugs': '1234,234d,2345',
        })
        self.assertFalse(form.is_valid())
        # no commas
        form = SprintBugsForm(instance=self.s, data={
            'new_bugs': '12342342345',
        })
        self.assertTrue(form.is_valid())
        # blank
        form = SprintBugsForm(instance=self.s, data={
            'new_bugs': '',
        })
        self.assertFalse(form.is_valid())
        form = SprintBugsForm(instance=self.s, data={
            'new_bugs': '1234,23465,2345',
        })
        self.assertTrue(form.is_valid())


class TestForms(TestCase):
    fixtures = ['test_data.json']

    def test_bugzilla_url(self):
        form_data = {"url": "http://localhost/?bugs"}
        form = BZURLForm(form_data)
        eq_(False, form.is_valid())
        ok_('url' in form.errors.keys())
        form_data = {"url": "https://bugzilla.mozilla.org/"
                            "buglist.cgi?cmdtype=runnamed;"
                            "namedcmd=mdn_20120410;list_id=2693036"}
        form = BZURLForm(form_data)
        eq_(False, form.is_valid())
        ok_('url' in form.errors.keys())
        form_data = {"url": GOOD_BZ_URL}
        form = BZURLForm(form_data)
        eq_(True, form.is_valid())

    def test_create_project_form(self):
        form_data = {
            'name': 'Best Project Ever',
            'slug': 'srsly',
            'team': 1,
            'url': 'not a url',
        }
        form = CreateProjectForm(form_data)
        eq_(False, form.is_valid())
        ok_('url' in form.errors)
        form_data['url'] = GOOD_BZ_URL
        form = CreateProjectForm(form_data)
        eq_(True, form.is_valid())
        project = form.save()
        eq_(project.urls.count(), 1)
        eq_(project.urls.all()[0].url, GOOD_BZ_URL)
        # no url required
        form = CreateProjectForm({
            'name': 'FO REAL Best Ever',
            'slug': 'srsly-fo-real',
            'team': 1,
        })
        eq_(True, form.is_valid())

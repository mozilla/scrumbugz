from __future__ import absolute_import
from copy import deepcopy
from datetime import date, timedelta

from mock import Mock, patch
from nose.tools import eq_, ok_

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import simplejson as json

from .forms import BZURLForm, CreateProjectForm, SprintBugsForm
from .models import Bug, BugSprintLog, BugzillaURL, CachedBug, Sprint
from scrum import models as scrum_models


scrum_models.BZAPI = Mock()
BUG_DATA_FILE = settings.PROJECT_DIR.child('scrum')\
                                    .child('test_data')\
                                    .child('bugzilla_data.json')
with open(BUG_DATA_FILE) as bdf:
    BUG_DATA = json.load(bdf)

GOOD_BZ_URL = BUG_DATA['bz_url']

# have to deepcopy to avoid cross-test-pollution
scrum_models.BZAPI.bug.get.side_effect = lambda *x, **y: deepcopy(BUG_DATA)


class TestBug(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        cache.clear()
        self.s = Sprint.objects.get(slug='2.2')

    @patch.object(Bug, 'points_history')
    def test_points_for_date_default(self, mock_bug):
        """ should default to points in whiteboard """
        bugs = self.s.get_bugs()
        b = bugs[0]
        eq_(b.story_points, b.points_for_date(date.today()))

    def test_db_cached_bugs(self):
        bugs = self.s.get_bugs()
        compare_fields = [
            'summary',
            'status',
            'whiteboard',
            'product',
            'component',
        ]
        for bug in bugs:
            cbug = CachedBug.objects.get(id=bug.id)
            for fieldname in compare_fields:
                self.assertEqual(getattr(bug, fieldname),
                                 getattr(cbug, fieldname))


class TestProject(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        cache.clear()
        self.s = Sprint.objects.get(slug='2.2')
        self.p = self.s.project

    def test_refreshing_bugs_not_remove_from_sprint(self):
        """
        Refreshing bugs from Bugzilla does not remove them from a sprint.
        """
        bugs = self.s.get_bugs(scrum_only=False)
        self.assertEqual(
            CachedBug.objects.filter(sprint__isnull=True).count(),
            len(bugs)
        )
        self.s.update_backlog_bugs(bugs)
        self.assertEqual(CachedBug.objects.filter(sprint=self.s).count(),
                         len(bugs))
        self.s.get_bugs(refresh=True)
        self.assertEqual(CachedBug.objects.filter(sprint=self.s).count(),
                         len(bugs))


class TestSprint(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        cache.clear()
        self.s = Sprint.objects.get(slug='2.2')

    def test_sprint_creation(self):
        User.objects.create_superuser('admin', 'admin@admin.com', 'admin')
        self.client.login(username='admin', password='admin')
        p = self.s.project
        fdata = {
            'name': '1.3.37',
            'slug': '1.3.37',
            'start_date': '2012-01-01',
            'end_date': '2012-01-15',
            'url': GOOD_BZ_URL,
        }
        url = reverse('scrum_sprint_new', args=[p.slug])
        resp = self.client.post(url, fdata, follow=True)
        self.assertRedirects(resp, reverse('scrum_sprint', kwargs={
            'pslug': p.slug,
            'sslug': '1.3.37',
        }))
        s = Sprint.objects.get(slug='1.3.37')
        self.assertEqual(s.urls.count(), 1)

    def test_get_products(self):
        products = self.s.get_products()
        eq_(2, len(products))
        ok_('mozilla.org' in products)

    def test_get_components(self):
        components = self.s.get_components()
        eq_(11, len(components))
        ok_('Website' in components)

    def test_sprint_bug_logging(self):
        bzurl = BugzillaURL.objects.create(
            url='http://example.com/?stuff=whatnot'
        )
        bugs = bzurl.get_bugs(scrum_only=False)
        bug_ids = set(int(bug.id) for bug in bugs)
        cbug_ids = set(bug.id for bug in CachedBug.objects.all())
        self.assertSetEqual(bug_ids, cbug_ids)
        self.assertEqual(0, BugSprintLog.objects.count())
        bugs = self.s.get_bugs(scrum_only=False)
        self.s.update_backlog_bugs(bugs)
        self.assertEqual(len(bugs), BugSprintLog.objects.count())
        action = CachedBug.objects.all()[0].sprint_actions.all()[0].action
        self.assertEqual(action, BugSprintLog.ADDED)

    def test_sprint_bug_move_logging(self):
        self.s.update_backlog_bugs(self.s.get_bugs())
        newsprint = Sprint.objects.create(
            name='New Sprint',
            slug='newsprint',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            project=self.s.project
        )
        bug = CachedBug.objects.get(id=665747)
        bug.sprint = None
        bug.save()
        self.assertEqual(BugSprintLog.REMOVED,
                         bug.sprint_actions.all()[0].action)
        bug.sprint = newsprint
        bug.save()
        self.assertEqual(BugSprintLog.ADDED,
                         bug.sprint_actions.all()[0].action)

    def test_sprint_bug_steal_logging(self):
        self.s.update_backlog_bugs(self.s.get_bugs(scrum_only=False))
        newsprint = Sprint.objects.create(
            name='New Sprint',
            slug='newsprint',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            project=self.s.project
        )
        bug = CachedBug.objects.get(id=665747)
        self.assertEqual(bug.sprint, self.s)
        bug.sprint = newsprint
        bug.save()
        self.assertEqual(bug.sprint_actions.count(), 3)
        self.assertEqual(BugSprintLog.REMOVED,
                         bug.sprint_actions.all()[1].action)
        self.assertEqual(BugSprintLog.ADDED,
                         bug.sprint_actions.all()[0].action)

    def test_backlog_bug_sync(self):
        self.s.update_backlog_bugs(self.s.get_bugs())
        self.s.backlog_bugs.remove(CachedBug.objects.get(id=665747))
        self.assertEqual(self.s.backlog_bugs.count(), 35)
        new_bug_ids = [665747, 758377, 766608]
        self.s.update_backlog_bugs(new_bug_ids)
        self.assertEqual(self.s.backlog_bugs.count(), 3)
        all_bl_bug_ids = self.s.backlog_bugs.values_list('id', flat=True)
        self.assertSetEqual(set(all_bl_bug_ids), set(new_bug_ids))
        # the process of syncing did not remove bugs unnecessarily
        self.assertEqual(self.s.bug_actions.filter(
            bug_id__in=[758377, 766608],
            action=BugSprintLog.REMOVED,
        ).count(), 0)
        # the bug was added back, thus the 2 ADDED actions.
        self.assertEqual(self.s.bug_actions.filter(
            bug_id=665747,
            action=BugSprintLog.ADDED
        ).count(), 2)

    def test_sprint_bug_management(self):
        self.s.update_backlog_bugs(self.s.get_bugs(scrum_only=False))
        self.s.backlog_bugs.remove(CachedBug.objects.get(id=665747))
        self.assertEqual(self.s.backlog_bugs.count(), 36)
        new_bug_ids = [665747, 758377, 766608]
        form = SprintBugsForm(instance=self.s, data={
            'sprint_bugs': ','.join(str(bid) for bid in new_bug_ids),
        })
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(self.s.backlog_bugs.count(), 3)
        all_bl_bug_ids = self.s.backlog_bugs.values_list('id', flat=True)
        self.assertSetEqual(set(all_bl_bug_ids), set(new_bug_ids))

    def test_sprint_bugs_form_validation(self):
        # non digit
        form = SprintBugsForm(instance=self.s, data={
            'sprint_bugs': '1234,234d,2345',
        })
        self.assertFalse(form.is_valid())
        # no commas
        form = SprintBugsForm(instance=self.s, data={
            'sprint_bugs': '12342342345',
        })
        self.assertTrue(form.is_valid())
        # blank
        form = SprintBugsForm(instance=self.s, data={
            'sprint_bugs': '',
        })
        self.assertFalse(form.is_valid())
        form = SprintBugsForm(instance=self.s, data={
            'sprint_bugs': '1234,23465,2345',
        })
        self.assertTrue(form.is_valid())


class TestForms(TestCase):

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
            'url': 'not a url',
        }
        form = CreateProjectForm(form_data)
        eq_(False, form.is_valid())
        ok_('url' in form.errors.keys())
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
        })
        eq_(True, form.is_valid())

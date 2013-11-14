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

from scrum import cron as scrum_cron
from scrum import models as scrum_models
from scrum import tasks as scrum_tasks
from scrum.forms import CreateProjectForm, SprintBugsForm
from scrum.models import BugSprintLog, Bug, BZProduct, Project, Sprint
from scrum.tasks import update_product
from scrum.utils import parse_whiteboard


scrum_models.bugzilla = Mock()
scrum_tasks.bugzilla = Mock()
TEST_DATA = settings.PROJECT_DIR.child('scrum', 'test_data')
BUG_DATA_FILE = TEST_DATA.child('bugzilla_data.json')

with open(BUG_DATA_FILE) as bdf:
    BUG_DATA = json.load(bdf)

GOOD_BZ_URL = BUG_DATA['bz_url']

# have to deepcopy to avoid cross-test-pollution
scrum_models.bugzilla.get_bugs.side_effect = lambda *x, **y: deepcopy(BUG_DATA)
scrum_tasks.bugzilla.get_bugs.side_effect = lambda *x, **y: deepcopy(BUG_DATA)


def get_bug_ids_mock(**kwargs):
    return [b['id'] for b in BUG_DATA.copy()['bugs']]


scrum_models.bugzilla.get_bug_ids.side_effect = get_bug_ids_mock
scrum_tasks.bugzilla.get_bug_ids.side_effect = get_bug_ids_mock


class TestUtils(TestCase):
    def test_parse_whiteboard(self):
        """parse_whiteboard() should return the correct data."""
        wbd = parse_whiteboard('u=dude c=bowling p=10')
        self.assertDictEqual(wbd, {
            'u': 'dude',
            'c': 'bowling',
            'p': '10',
        })

    def test_parse_whiteboard_brackets(self):
        """parse_whiteboard() should return the correct data with brackets."""
        wbd = parse_whiteboard('things,[u=dude c=bowling p=10] other stuff')
        self.assertDictEqual(wbd, {
            'u': 'dude',
            'c': 'bowling',
            'p': '10',
        })

    def test_parse_whiteboard_commas(self):
        """parse_whiteboard() should return the correct data with commas."""
        wbd = parse_whiteboard('things,u=dude c=bowling,p=10,[qawanted]')
        self.assertDictEqual(wbd, {
            'u': 'dude',
            'c': 'bowling',
            'p': '10',
        })


class TestBZProducts(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.p = Project.objects.get(slug='mdn')
        BZProduct.objects._reset_full_list()

    def test_products_dict_no_overlap(self):
        """
        There was an issue where if one project was following all components in
        a product, and another just a specific component, the specific one would
        override the ALL one and the other bugs wouldn't be looked at for
        updating via email.
        """
        BZProduct.objects.all().delete()
        BZProduct.objects.create(name='Dude',
                                 component='Abiding',
                                 project=self.p)
        BZProduct.objects.create(name='Dude',
                                 component=scrum_models.ALL_COMPONENTS,
                                 project=self.p)
        all_prods = scrum_models.get_bzproducts_dict(BZProduct.objects.all())
        self.assertDictEqual(all_prods,
                             {u'Dude': [unicode(scrum_models.ALL_COMPONENTS)]})


class TestCron(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.s = Sprint.objects.get(slug='2.2')
        self.p = Project.objects.get(pk=1)
        update_product('MDN')

    def test_fix_projectless_bugs(self):
        self.s.update_bugs(self.p.get_backlog())
        eq_(self.s.bugs.filter(project__isnull=True).count(), 9)
        scrum_cron.fix_projectless_bugs()
        proj_bugs = set()
        for proj in self.p.team.projects.all():
            proj_bugs |= set(proj.bugs.all())
        self.assertSetEqual(set(self.s.bugs.all()), proj_bugs)


class TestBug(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        cache.clear()
        self.s = Sprint.objects.get(slug='2.2')
        self.p = Project.objects.get(pk=1)
        self.p.products.create(name='Input',
                               component=scrum_models.ALL_COMPONENTS)
        update_product('MDN')

    def test_has_scrum_data(self):
        """
        A bug with u= or c= or p= with no data should still show up.
        """
        b = Bug.objects.get(id=784492)
        ok_(b.has_scrum_data)

    def test_scrum_data_c_defaults_component(self):
        """
        A bug with no or blank c= should use BZ component.
        """
        b = Bug.objects.get(id=784492)
        eq_(b.component, b.story_component)

    def test_scrum_only_queryset(self):
        bugs = Bug.objects.scrum_only()
        b = Bug.objects.get(id=784492)
        ok_(b in bugs)

    def test_whiteboard_update(self):
        b = Bug.objects.get(id=778465)
        eq_(b.story_points, 1)
        eq_(b.story_user, 'dev')

    def test_whiteboard_clearable(self):
        b = Bug.objects.get(id=778465)
        b.whiteboard = ''
        b.save()
        eq_(b.story_points, 0)
        eq_(b.story_user, '')

    def test_whiteboard_add_to_sprint(self):
        """
        Specifying `s=SPRINT_SLUG` in the whiteboard should add the bug to
        the sprint if it exists.
        """
        b = Bug.objects.get(id=778465)
        assert b.sprint is None
        assert b.project is None
        b.whiteboard += ' s=2.2'
        b.save()
        b = Bug.objects.get(id=778465)
        eq_(b.sprint, self.s)
        eq_(b.project, self.p)

    def test_whiteboard_change_moves_bug_to_new_sprint(self):
        """ Changes to the s= whiteboard tag should move the bug. """
        self.test_whiteboard_add_to_sprint()
        newsprint = Sprint.objects.create(
            name='New Sprint',
            slug='newsprint',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            team=self.s.team
        )
        b = Bug.objects.get(id=778465)
        b.whiteboard += ' s=newsprint'
        b.save()
        b = Bug.objects.get(id=778465)
        eq_(b.sprint, newsprint)

    def test_whiteboard_sprint_moves_logged(self):
        """ Bugs added to and removed from sprints should be in the log. """
        self.test_whiteboard_change_moves_bug_to_new_sprint()
        logs = BugSprintLog.objects.filter(bug_id=778465,
                                           action=BugSprintLog.ADDED)
        eq_(logs.count(), 2)
        logs = BugSprintLog.objects.filter(bug_id=778465,
                                           action=BugSprintLog.REMOVED)
        eq_(logs.count(), 1)

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
        b = Bug.objects.get(id=778466)
        eq_(b.depends_on, [778465])
        b = Bug.objects.get(id=781714)
        eq_(b.depends_on, [781709, 781721])

    def test_blocked_bugs(self):
        self.assertSetEqual(set([778466, 781718, 781715, 781717, 781718]),
                            set(Bug.objects.get_blocked().keys()))
        b = Bug.objects.get(id=778465)
        b.status = 'RESOLVED'
        b.save()
        self.assertSetEqual(set([781718, 781715, 781717, 781718]),
                            set(Bug.objects.get_blocked().keys()))

    def test_flagged_bugs(self):
        self.assertSetEqual(set([778465, 781710, 781717]),
                            set(Bug.objects.get_flagged()))

    def test_bugs_with_attachments(self):
        b = Bug.objects.get(id=778465)
        self.assertSetEqual(set(['review', 'feedback', 'superreview', 'ui-review']),
                            set(b.bucketed_flags.keys()))
        self.assertSetEqual(set(['review', 'feedback', 'superreview', 'ui-review']),
                            set(b.flags_status.keys()))
        self.assertEqual('plus', b.flags_status.get('review'))
        self.assertEqual('question', b.flags_status.get('superreview'))
        self.assertEqual('question', b.flags_status.get('ui-review'))
        self.assertEqual('question', b.flags_status.get('feedback'))

    def test_bug_938346(self):
        """
        Tests Bug 938346 - attachment flag labeling doesn't ignore obsolete attachments
        """
        b = Bug.objects.get(id=778465)
        ref_ids = []
        for flag_name, flags in b.bucketed_flags.iteritems():
            for flag in flags:
                if 'ref_id' in flag:
                    ref_ids.append(flag['ref_id'])
        self.assertSetEqual(set([829407, 830313]),
                            set(ref_ids))
        
    def test_get_by_products(self):
        eq_(Bug.objects.by_products(self.p.get_products()).count(), 11)
        b = Bug.objects.get(id=778466)
        b.product = 'The Bot Lebowski'
        b.save()
        eq_(Bug.objects.by_products(self.p.get_products()).count(), 10)
        eq_(Bug.objects.by_products({}).count(), 0)

    def test_projects_from_product(self):
        """
        Bug.projects_from_product should return all projects with which
        a bug is potentially associated.
        """
        search_bug = Bug.objects.get(id=781717)
        eq_(len(search_bug.projects_from_product()), 2)
        non_search_bug = Bug.objects.get(id=781715)
        eq_(len(non_search_bug.projects_from_product()), 1)


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


class TestSprint(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        cache.clear()
        self.s = Sprint.objects.get(slug='2.2')
        self.p = Project.objects.get(pk=1)
        self.p.products.create(name='Input',
                               component=scrum_models.ALL_COMPONENTS)
        self.p.products.create(name='Lebowski Enterprise',
                               component='Urban Achievers')
        self.p.products.create(name='Lebowski Enterprise',
                               component='Rugs')

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

    def test_sprint_editing(self):
        User.objects.create_superuser('admin', 'admin@admin.com', 'admin')
        self.client.login(username='admin', password='admin')
        t = self.s.team
        fdata = {
            'name': '1.3.37',
            'slug': '1.3.37',
            'start_date': '2012-01-01',
            'end_date': '2012-01-15',
        }
        url = reverse('scrum_sprint_edit', args=[t.slug, self.s.slug])
        resp = self.client.post(url, fdata, follow=True)
        self.assertRedirects(resp, reverse('scrum_sprint', kwargs={
            'slug': t.slug,
            'sslug': '1.3.37',
        }))

    def test_get_products(self):
        prods = self.p.get_products()
        expected = {
            'Input': ['__ALL__'],
            'Lebowski Enterprise': ['Rugs', 'Urban Achievers'],
        }
        self.assertSetEqual(set(prods.keys()), set(expected.keys()))
        for prod in expected.keys():
            self.assertSetEqual(set(prods[prod]), set(expected[prod]))

    def test_get_components(self):
        self.assertSetEqual(set(self.p.get_components()),
                            set(['Urban Achievers', 'Rugs']))
        self.p.products.create(name='The Dude', component='Bowling')
        self.assertSetEqual(set(self.p.get_components()),
                            set(['Urban Achievers', 'Rugs', 'Bowling']))

    def test_sprint_bug_logging(self):
        bugs = self.p.get_backlog(scrum_only=False)
        self.assertSetEqual(set(bugs), set(Bug.objects.open()))
        self.assertEqual(0, BugSprintLog.objects.count())
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
        bug = Bug.objects.get(id=778465)
        self.s.update_bugs(remove=[778465])
        self.assertEqual(BugSprintLog.REMOVED,
                         bug.sprint_actions.all()[0].action)
        newsprint.update_bugs([778465])
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
        bug = Bug.objects.get(id=781714)
        self.assertEqual(bug.sprint, None)
        bug = Bug.objects.get(id=778465)
        self.assertEqual(bug.sprint, self.s)
        newsprint.update_bugs([778465])
        self.assertEqual(bug.sprint_actions.count(), 3)
        self.assertEqual(BugSprintLog.REMOVED,
                         bug.sprint_actions.all()[1].action)
        self.assertEqual(BugSprintLog.ADDED,
                         bug.sprint_actions.all()[0].action)

    def test_backlog_bug_sync(self):
        self.s.update_bugs(self.p.get_backlog())
        self.assertEqual(self.s.bug_actions.filter(
            bug_id=778465,
            action=BugSprintLog.ADDED
        ).count(), 1)
        self.s.update_bugs(remove=[778465])
        self.assertEqual(self.s.bugs.count(), 8)
        new_bug_ids = [778465, 778466, 781717]
        self.s.update_bugs([778465], self.s.bugs.exclude(id__in=new_bug_ids))
        self.assertEqual(self.s.bugs.count(), 3)
        all_bl_bug_ids = self.s.bugs.values_list('id', flat=True)
        self.assertSetEqual(set(all_bl_bug_ids), set(new_bug_ids))
        # the process of syncing did not remove bugs unnecessarily
        self.assertEqual(self.s.bug_actions.filter(
            bug_id__in=[778466, 781717],
            action=BugSprintLog.REMOVED,
        ).count(), 0)
        # the bug was added back, thus the 2 ADDED actions.
        print self.s.bug_actions.filter(bug_id=778465)
        self.assertEqual(self.s.bug_actions.filter(
            bug_id=778465,
            action=BugSprintLog.ADDED
        ).count(), 2)

    def test_sprint_bug_management(self):
        self.s.update_bugs(self.p.get_backlog())
        self.s.update_bugs(remove=[778465])
        self.assertEqual(self.s.bugs.count(), 8)
        new_bug_ids = [778465, 778466, 781717]
        form = SprintBugsForm(instance=self.s, data={
            'add_bugs': '778465',
            'remove_bugs': ','.join(str(b.id) for b in
                                    self.s.bugs.exclude(id__in=new_bug_ids)),
        })
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(self.s.bugs.count(), 3)
        all_bl_bug_ids = self.s.bugs.values_list('id', flat=True)
        self.assertSetEqual(set(all_bl_bug_ids), set(new_bug_ids))

    def test_sprint_bugs_form_validation(self):
        # non digit
        form = SprintBugsForm(instance=self.s, data={
            'add_bugs': '1234,234d,2345',
        })
        self.assertFalse(form.is_valid())
        # no commas
        form = SprintBugsForm(instance=self.s, data={
            'add_bugs': '12342342345',
        })
        self.assertTrue(form.is_valid())
        # blank
        form = SprintBugsForm(instance=self.s, data={
            'add_bugs': '',
        })
        self.assertTrue(form.is_valid())
        form = SprintBugsForm(instance=self.s, data={
            'add_bugs': '1234,23465,2345',
        })
        self.assertTrue(form.is_valid())


class TestForms(TestCase):
    fixtures = ['test_data.json']

    def test_create_project_form(self):
        form_data = {
            'name': 'Best Project Ever',
            'slug': 'srsly',
            'team': 1,
            'product': 'Websites',
        }
        form = CreateProjectForm(form_data)
        eq_(False, form.is_valid())
        ok_('product' in form.errors)
        form_data['product'] = 'Websites/__ALL__'
        form = CreateProjectForm(form_data)
        eq_(True, form.is_valid())
        project = form.save()
        eq_(project.products.count(), 1)
        eq_(project.products.all()[0].name, 'Websites')
        eq_(project.products.all()[0].component, scrum_models.ALL_COMPONENTS)
        # no product required
        form = CreateProjectForm({
            'name': 'FO REAL Best Ever',
            'slug': 'srsly-fo-real',
            'team': 1,
        })
        eq_(True, form.is_valid())

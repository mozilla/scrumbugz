from __future__ import absolute_import
from datetime import date

from mock import Mock, patch
from nose.tools import eq_, ok_

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.utils import simplejson as json

from .forms import BZURLForm
from .models import Bug, CachedBug, Sprint
from scrum import models as scrum_models


scrum_models.BZAPI = Mock()
BUG_DATA_FILE = settings.PROJECT_DIR.child('scrum')\
                                    .child('test_data')\
                                    .child('bugzilla_data.json')
with open(BUG_DATA_FILE) as bdf:
    BUG_DATA = json.load(bdf)

GOOD_BZ_URL = BUG_DATA['bz_url']
scrum_models.BZAPI.bug.get.return_value = BUG_DATA


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


class TestSprint(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.s = Sprint.objects.get(slug='2.2')

    def test_get_products(self):
        products = self.s.get_products()
        eq_(2, len(products))
        ok_('mozilla.org' in products)

    def test_get_components(self):
        components = self.s.get_components()
        eq_(11, len(components))
        ok_('Website' in components)


class TestSprintForm(TestCase):

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

"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import date

from mock import patch
from nose.tools import eq_, ok_

from django.test import TestCase

from forms import SprintForm
from models import Sprint, Bug


GOOD_BZ_URL = "https://bugzilla.mozilla.org/buglist.cgi?list_id=2692959;"
"columnlist=opendate%2Cassigned_to%2Cbug_status%2Cresolution%2Cshort_desc"
"%2Cstatus_whiteboard%2Ckeywords;emailtype1=exact;query_based_on=mdn_20120410;"
"status_whiteboard_type=allwordssubstr;query_format=advanced;"
"status_whiteboard=s%3D2012-04-10;email1=nobody%40mozilla.org;"
"component=Administration;component=Deki%20Infrastructure;component=Demos;"
"component=Docs%20Platform;component=Documentation%20Requests;"
"component=Engagement;component=Evangelism;component=Forums;"
"component=Localization;component=Upload%20Requests;component=Website;"
"product=Mozilla%20Developer%20Network;target_milestone=---;"
"target_milestone=2.7;known_name=mdn_20120410"


class TestBug(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.s = Sprint.objects.get(slug='2.2')

    @patch.object(Bug, 'points_history')
    def test_points_for_date_default(self, mock_bug):
        """ should default to points in whiteboard """
        bugs = self.s.get_bugs()
        b = bugs[0]
        eq_(b.story_points, b.points_for_date(date.today()))


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

    def setUp(self):
        self.form_data = {
            'project': '1',
            'name': 'test',
            'slug': 'test',
            'start_date': date.today(),
            'end_date': date.today(),
            'bz_url': ''
        }

    def test_bugzilla_url(self):
        self.form_data.update({"bz_url": "http://localhost/?bugs"})
        form = SprintForm(self.form_data)
        eq_(False, form.is_valid())
        ok_('bz_url' in form.errors.keys())
        self.form_data.update({"bz_url": "https://bugzilla.mozilla.org/"
                               "buglist.cgi?cmdtype=runnamed;"
                               "namedcmd=mdn_20120410;list_id=2693036"})
        form = SprintForm(self.form_data)
        eq_(False, form.is_valid())
        ok_('bz_url' in form.errors.keys())
        self.form_data.update({"bz_url": GOOD_BZ_URL})
        form = SprintForm(self.form_data)
        eq_(True, form.is_valid())

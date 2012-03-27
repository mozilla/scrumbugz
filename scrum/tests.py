"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from nose.tools import eq_, ok_

from django.test import TestCase

from models import Sprint


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

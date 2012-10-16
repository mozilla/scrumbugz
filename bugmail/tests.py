from email.parser import Parser

from django.conf import settings
from django.test import TestCase

from mock import Mock
from nose.tools import eq_, ok_

from bugmail import utils as scrum_email
from scrum import models as scrum_models


TEST_DATA = settings.PROJECT_DIR.child('bugmail', 'test_data')
BUGMAIL_FILES = (
    TEST_DATA.child('bugmail.txt'),
    TEST_DATA.child('bugmail2.txt'),
)


def get_messages_mock(delete=True):
    msgs = []
    for fn in BUGMAIL_FILES:
        with open(fn) as bmf:
            msgs.append(Parser().parse(bmf))
    return msgs


scrum_email.get_messages = Mock()
scrum_email.get_messages.side_effect = get_messages_mock


class TestEmail(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        scrum_models.BZProduct.objects._reset_full_list()

    def test_is_bugmail(self):
        m = scrum_email.get_messages()[0]
        ok_(scrum_email.is_bugmail(m))
        del m['x-bugzilla-type']
        ok_(not scrum_email.is_bugmail(m))

    def test_get_bugmails(self):
        good_data = [760693, 760694]
        eq_(good_data, sorted(scrum_email.get_bugmails().keys()))

    def test_not_is_interesting(self):
        for msg in scrum_email.get_bugmails().values():
            print scrum_email.is_interesting(msg)
            ok_(not scrum_email.is_interesting(msg))
        p = scrum_models.Project.objects.get(pk=1)
        p.products.create(name='Input')
        scrum_models.BZProduct.objects._reset_full_list()
        for msg in scrum_email.get_bugmails().values():
            ok_(not scrum_email.is_interesting(msg))
        p.products.create(name='Websites', component='Betafarm')
        scrum_models.BZProduct.objects._reset_full_list()
        for msg in scrum_email.get_bugmails().values():
            ok_(not scrum_email.is_interesting(msg))

    def test_is_interesting(self):
        p = scrum_models.Project.objects.get(pk=1)
        comp = p.products.create(name='Websites', component='Scrumbugs')
        for msg in scrum_email.get_bugmails().values():
            ok_(scrum_email.is_interesting(msg))
        comp.delete()
        scrum_models.BZProduct.objects._reset_full_list()
        for msg in scrum_email.get_bugmails().values():
            ok_(not scrum_email.is_interesting(msg))
        p.products.create(name='Websites')
        scrum_models.BZProduct.objects._reset_full_list()
        for msg in scrum_email.get_bugmails().values():
            ok_(scrum_email.is_interesting(msg))

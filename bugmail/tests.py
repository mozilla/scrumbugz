from datetime import timedelta
from email.parser import Parser

from django.conf import settings
from django.test import TestCase
from django.utils.timezone import now

from mock import Mock, patch
from nose.tools import eq_, ok_

from bugmail import utils as scrum_email
from bugmail import tasks as bm_tasks
from bugmail.models import BugmailStat
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


class TestTasks(TestCase):
    def test_log_clean_deletes(self):
        week_ago = (now() - timedelta(days=7)).date()
        months_ago = (now() - timedelta(days=60)).date()
        b1 = BugmailStat.objects.create(stat_type=BugmailStat.TOTAL,
                                        count=5,
                                        date=week_ago)
        BugmailStat.objects.create(stat_type=BugmailStat.TOTAL,
                                   count=5,
                                   date=months_ago)
        eq_(BugmailStat.objects.count(), 2)
        bm_tasks.clean_bugmail_log()
        eq_(BugmailStat.objects.count(), 1)
        eq_(BugmailStat.objects.all()[0], b1)


@patch('scrum.tasks.update_product', Mock())
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
        p = scrum_models.Project.objects.get(pk=1)
        p.products.create(name='Websites', component='Scrumbugs')
        scrum_models.BZProduct.objects._reset_full_list()
        eq_(good_data, sorted(scrum_email.get_bugmails().keys()))

    def test_not_is_interesting(self):
        for msg in scrum_email.get_bugmails().values():
            print scrum_email.is_interesting(msg)
            ok_(not scrum_email.is_interesting(msg))
        p = scrum_models.Project.objects.get(pk=1)
        p.products.create(name='Input', component=scrum_models.ALL_COMPONENTS)
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
        p.products.create(name='Websites',
                          component=scrum_models.ALL_COMPONENTS)
        scrum_models.BZProduct.objects._reset_full_list()
        for msg in scrum_email.get_bugmails().values():
            ok_(scrum_email.is_interesting(msg))

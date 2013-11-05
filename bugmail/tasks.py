import logging
from datetime import timedelta

from django.utils.timezone import now

from celery import task

from bugmail.models import BugmailStat
from bugmail.utils import get_bugmails, store_messages
from scrum.tasks import update_bugs


log = logging.getLogger(__name__)


@task(name='get_bugmails')
def get_bugmail_messages():
    """
    Check bugmail for updated bugs, and get their data from Bugzilla.
    """
    msgs = get_bugmails()
    bugids = store_messages(msgs)
    if bugids:
        update_bugs.delay(bugids)


@task(name='clean_bugmail_log')
def clean_bugmail_log():
    """
    Delete old bugmail stats log entries.
    """
    month_ago = (now() - timedelta(days=30)).date()
    BugmailStat.objects.filter(date__lt=month_ago).delete()

import logging

from celery import task

from bugmail.utils import extract_bug_info, get_bugmails
from scrum.models import Bug
from scrum.tasks import update_bugs

try:
    import newrelic.agent
except ImportError:
    newrelic = False


log = logging.getLogger(__name__)


@task(name='get_bugmails')
def get_bugmail_messages():
    """
    Check bugmail for updated bugs, and get their data from Bugzilla.
    """
    msgs = get_bugmails()
    if msgs:
        for bid, msg in msgs.iteritems():
            bug_data = extract_bug_info(msg)
            bug, created = Bug.objects.get_or_create(id=bid, defaults=bug_data)
            if not created:
                for attr, val in bug_data.items():
                    setattr(bug, attr, val)
                bug.save()
        bugids = msgs.keys()
        update_bugs.delay(bugids)
        numbugs = len(bugids)
        if newrelic:
            newrelic.agent.record_custom_metric('Custom/Bugmails', numbugs)
        log.info('Synced %d bug(s) from email', numbugs)

import logging

from celery import task

from bugzilla.api import bugzilla
from scrum.bugmail import extract_bug_info, get_bugmails
from scrum.models import Bug, store_bugs


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


@task(name='update_product')
def update_product(product, component=None):
    kwargs = {'product': product, 'scrum_only': False}
    if component:
        kwargs['component'] = component
    store_bugs(bugzilla.get_bugs(**kwargs))


@task(name='update_bugs')
def update_bugs(bug_ids):
    store_bugs(bugzilla.get_bugs(ids=bug_ids, scrum_only=False))

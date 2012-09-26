import logging

from celery import task

from bugzilla.api import bugzilla
from scrum.bugmail import extract_bug_info, get_bugmails
from scrum.models import Bug, store_bugs
from scrum.utils import chunked

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
    kwargs = {'product': product, 'scrum_only': True}
    if component:
        kwargs['component'] = component
    bug_ids = bugzilla.get_bug_ids(**kwargs)
    log.debug('Updating %d bugs from %s', len(bug_ids), kwargs)
    for bids in chunked(bug_ids, 100):
        update_bugs.delay(bids)


@task(name='update_bugs')
def update_bugs(bug_ids):
    bugs = bugzilla.get_bugs(ids=bug_ids, scrum_only=False)
    for fault in bugs['faults']:
        if fault['faultCode'] == 102:  # unauthorized
            try:
                Bug.objects.get(id=fault['id']).delete()
                log.warning("DELETED unauthorized bug #%d", fault['id'])
            except Bug.DoesNotExist:
                pass
    store_bugs(bugs)


def update_bug_chunks(bugs, chunk_size=100):
    """
    Update bugs in chunks of `chunk_size`.
    :param bugs: Iterable of bug objects.
    """
    numbugs = 0
    for bchunk in chunked(bugs, chunk_size):
        numbugs += len(bugs)
        log.debug("Updating %d bugs", len(bugs))
        update_bugs.delay([b.id for b in bchunk])
    log.debug("Total bugs updated: %d", numbugs)

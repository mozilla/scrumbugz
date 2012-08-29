from __future__ import absolute_import

import logging
import sys
from datetime import datetime, timedelta

from django.conf import settings

from cronjobs import register

from scrum.email import get_bugmails
from scrum.models import BugzillaURL, BZError, Sprint
from scrum.utils import get_bz_url_for_bug_ids


NEW_RELIC = False
try:
    import newrelic.agent
    NEW_RELIC = True
except ImportError:
    pass


CACHE_BUGS_FOR = timedelta(hours=getattr(settings, 'CACHE_BUGS_FOR', 4))
log = logging.getLogger(__name__)


@register
def sync_bugmail():
    """
    Check bugmail for updated bugs, and get their data from Bugzilla.
    """
    bugids = get_bugmails()
    if bugids:
        numbugs = len(bugids)
        url = BugzillaURL(url=get_bz_url_for_bug_ids(bugids))
        try:
            url.get_bugs(open_only=False)
        except BZError:
            # error logged in `get_bugs`
            log.error('Failed to update bugs from email: %s', bugids)
            return
        if NEW_RELIC:
            newrelic.agent.record_custom_metric('Custom/Bugmails', numbugs)
        log.info('Synced %d bug(s) from email', numbugs)


@register
def sync_backlogs():
    """
    Get the bugs data for all urls in the system updated more than
    CACHE_BUGS_FOR hours ago.
    """
    counter = 0
    synced_urls = []
    sync_time = datetime.utcnow() - CACHE_BUGS_FOR
    for url in BugzillaURL.objects.filter(date_synced__lt=sync_time):
        # avoid dupes
        # need to do this here instead of setting the DB column unique b/c
        # it is possible for 2 projects to use the same search url.
        if url.url in synced_urls:
            log.debug('Found dupe url: %s', url.url)
            if url.one_time:
                url.delete()
            continue
        synced_urls.append(url.url)
        try:
            url.get_bugs(open_only=False)
        except BZError:
            # error logged in `get_bugs`
            try:
                url.get_bugs(open_only=True)
            except BZError:
                continue
        if url.one_time:
            log.debug('Deleted url: %s', url.url)
            url.delete()
        log.debug('Synced url: %s', url.url)
        counter += 1
    if counter:
        log.info('Synced %d url(s)', counter)


@register
def sync_old_sprints():
    """
    Get the bugs from sprints with bugzilla urls and associate them properly.
    """
    for sprint in Sprint.objects.all():
        if sprint.bz_url:
            bzurl = BugzillaURL(url=sprint.bz_url)
            bugs = bzurl.get_bugs(scrum_only=False, open_only=False)
            for bug in bugs:
                # at this point project and sprint ids are equal
                bug.project_id = bug.backlog_id = sprint.team_id
                bug.sprint = sprint
                bug.save()
        sys.stdout.write('.')
        sys.stdout.flush()
    print '\nDone.'

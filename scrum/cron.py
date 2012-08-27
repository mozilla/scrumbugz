from __future__ import absolute_import

import logging
from datetime import datetime, timedelta

from django.conf import settings

from cronjobs import register

from scrum.email import get_bugmails
from scrum.models import BugzillaURL, BZError, Project
from scrum.utils import get_bz_url_for_bug_ids


CACHE_BUGS_FOR = timedelta(hours=getattr(settings, 'CACHE_BUGS_FOR', 4))
log = logging.getLogger(__name__)


@register
def sync_bugmail():
    """
    Check bugmail for updated bugs, and get their data from Bugzilla.
    """
    counter = 0
    bugids = get_bugmails()
    for slug, ids in bugids.items():
        log.debug('Got %d bugs for project %s', len(ids), slug)
        counter += len(ids)
        url = BugzillaURL(url=get_bz_url_for_bug_ids(ids))
        proj = None
        if slug:
            try:
                proj = Project.objects.get(slug=slug)
            except Project.DoesNotExist:
                pass
        if proj:
            url.project = proj
        try:
            url.get_bugs(open_only=False)
        except BZError:
            continue
    if counter:
        log.info('Synced %d bug(s) from email', counter)


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
            url.get_bugs(open_only=(not url.one_time))
        except BZError:
            continue
        if url.one_time:
            log.debug('Deleted url: %s', url.url)
            url.delete()
        log.debug('Synced url: %s', url.url)
        counter += 1
    if counter:
        log.info('Synced %d url(s)', counter)

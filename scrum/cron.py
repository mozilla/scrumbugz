from __future__ import absolute_import

import logging
import sys
from datetime import datetime, timedelta

from django.conf import settings

from cronjobs import register

from scrum.email import get_bugmails
from scrum.models import BugzillaURL, BZError, Project
from scrum.utils import get_bz_url_for_bug_ids


CACHE_BUGS_FOR = timedelta(hours=getattr(settings, 'CACHE_BUGS_FOR', 4))
logger = logging.getLogger('scrum.cron')


@register
def sync_bugmail():
    """
    Check bugmail for updated bugs, and get their data from Bugzilla.
    """
    counter = 0
    bugids = get_bugmails()
    for slug, ids in bugids.items():
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
        url.get_bugs()
        sys.stdout.write('.')
        sys.stdout.flush()
    if counter:
        print "\nSynced {0} bugs".format(counter)


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
            if url.one_time:
                url.delete()
            continue
        synced_urls.append(url.url)
        try:
            url.get_bugs()
        except BZError:
            logger.error('Problem fetching bugs from %s', url.url)
            continue
        if url.one_time:
            url.delete()
        sys.stdout.write('.')
        sys.stdout.flush()
        counter += 1
    if counter:
        print "\nSynced {0} urls".format(counter)

from __future__ import absolute_import

from cronjobs import register

from scrum.email import get_bugmails
from scrum.models import BugzillaURL, Project
from scrum.utils import get_bz_url_for_bug_ids


@register
def sync_bugs():
    """
    Check bugmail for updated bugs, and get their data from Bugzilla.
    """
    bugids = get_bugmails()
    for slug, ids in bugids.items():
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

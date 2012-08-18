from __future__ import absolute_import

from cronjobs import register

from scrum.email import get_bugmail_ids
from scrum.models import Bug


@register
def sync_bugs():
    """
    Check bugmail for updated bugs, and get their data from Bugzilla.
    """
    bugids = get_bugmail_ids()
    if bugids:
        Bug.objects.filter(id__in=bugids).sync_bugs()

from __future__ import absolute_import

from cronjobs import register

from scrum.email import get_bugmail_ids
from scrum.models import get_bz_url_for_buglist


@register
def sync_bugs():
    """
    Check bugmail for updated bugs, and get their datas from Bugzilla.
    """
    bugids = get_bugmail_ids()
    if bugids:
        url = get_bz_url_for_buglist(bugids)
        url.get_bugs(refresh=True)

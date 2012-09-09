from __future__ import absolute_import

import logging
import sys
from datetime import timedelta

from django.conf import settings

from cronjobs import register

from bugzilla.api import bugzilla
from scrum.models import BugzillaURL, BZProduct, Project, Sprint, store_bugs


CACHE_BUGS_FOR = timedelta(hours=getattr(settings, 'CACHE_BUGS_FOR', 4))
log = logging.getLogger(__name__)


@register
def move_project_urls_to_products():
    """
    Get products and components from legacy project urls and set them on
    the project.
    """
    bz_products = bugzilla.get_products_simplified()
    for url in BugzillaURL.objects.filter(project__isnull=False):
        products = url.get_products()
        components = url.get_components()
        for p in products:
            if p not in bz_products:
                continue
            c_in_prod = 0
            if components:
                for c in components:
                    if c not in bz_products[p]:
                        continue
                    BZProduct.objects.get_or_create(name=p,
                                                    component=c,
                                                    project_id=url.project_id)
                    c_in_prod += 1
            if not c_in_prod:
                BZProduct.objects.get_or_create(name=p,
                                                project_id=url.project_id)


@register
def sync_full_backlogs():
    """
    Get all bugs associated with all projects.

    USE EXTREMELY SPARINGLY
    """
    for proj in Project.objects.all():
        prods = proj.get_products()
        for prod, comps in prods.items():
            kwargs = {'product': prod, 'scrum_only': False}
            if comps:
                kwargs['component'] = comps[0] if len(comps) == 1 else comps
            store_bugs(bugzilla.get_bugs(**kwargs), proj)
            sys.stdout.write('.')
            sys.stdout.flush()
    print '\nDone.'


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

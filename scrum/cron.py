from __future__ import absolute_import

import logging
import sys

from django.core.cache import cache
from django.core.paginator import Paginator

from cronjobs import register

from scrum.models import Bug, BugzillaURL, BZProduct, Project, Sprint
from scrum.tasks import update_bug_chunks


log = logging.getLogger(__name__)


@register
def reprocess_bugs():
    """
    Fetch and resave all bugs so that their signals fire.
    """
    # we fetch bugs in chunks to reduce race condition chances
    pages = Paginator(Bug.objects.all(), 50)
    print 'Processing %d bugs' % pages.count
    for pnum in pages.page_range:
        for b in pages.page(pnum).object_list:
            b.save()
            sys.stdout.write('.')
            sys.stdout.flush()
    print '\nDone.'


@register
def clear_cache():
    cache.clear()


@register
def update_old_format_bugs():
    bugs = Bug.objects.filter(assigned_to__contains='||').only('id')
    update_bug_chunks(bugs)


@register
def move_project_urls_to_products():
    """
    Get products and components from legacy project urls and set them on
    the project.
    """
    for url in BugzillaURL.objects.filter(project__isnull=False):
        products = url.get_products()
        components = url.get_components()
        for p in products:
            c_in_prod = 0
            if components:
                for c in components:
                    BZProduct.objects.get_or_create(name=p,
                                                    component=c,
                                                    project_id=url.project_id)
                    c_in_prod += 1
            if not c_in_prod:
                BZProduct.objects.get_or_create(name=p,
                                                project_id=url.project_id)


@register
def fix_projectless_bugs():
    """
    Find bugs in sprints that have no project and give them one.
    """
    for project in Project.objects.all():
        product_bugs = Bug.objects.by_products(project.get_products())
        product_bugs.filter(sprint__isnull=False, project__isnull=True) \
                    .update(project=project)


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

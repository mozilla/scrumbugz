import logging
from datetime import timedelta
from collections import defaultdict

from django.core.cache import cache
from django.utils import simplejson as json
from django.utils.timezone import now
from django.views.generic import TemplateView

from bugmail.models import BugmailStat
from scrum.utils import date_range, date_to_js


log = logging.getLogger(__name__)


class BugmailStatsView(TemplateView):
    template_name = 'bugmail/bugmail_stats.html'
    cache_key = 'bugmail:stats:json'

    def get_context_data(self, **kwargs):
        context = super(BugmailStatsView, self).get_context_data(**kwargs)
        no_cache = self.request.META.get('HTTP_CACHE_CONTROL') == 'no-cache'
        json_stats = None if no_cache else cache.get(self.cache_key)

        if not json_stats:
            wks_ago = (now() - timedelta(days=14)).date()
            stats = BugmailStat.objects.stats_for_range(wks_ago)
            stats_dict = {
                BugmailStat.TOTAL: defaultdict(int),
                BugmailStat.USED: defaultdict(int),
            }
            for s in stats:
                stats_dict[s.stat_type][date_to_js(s.date)] += s.count
            all_stats = {
                'total': [],
                'used': [],
                'x_axis': [],
            }
            stats_total = stats_dict[BugmailStat.TOTAL]
            stats_used = stats_dict[BugmailStat.USED]
            for d in date_range(wks_ago):
                d = date_to_js(d)
                all_stats['x_axis'].append(d)
                all_stats['total'].append([d, stats_total[d]])
                all_stats['used'].append([d, stats_used[d]])
            json_stats = json.dumps(all_stats)
            cache.set(self.cache_key, json_stats, 1800)  # 30 minutes
        context['stats'] = json_stats
        return context

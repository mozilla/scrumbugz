import logging
from datetime import timedelta
from collections import defaultdict

from django.utils import simplejson as json
from django.utils.timezone import now
from django.views.generic import TemplateView

from bugmail.models import BugmailStat
from scrum.utils import date_range, date_to_js


log = logging.getLogger(__name__)


class BugmailStatsView(TemplateView):
    template_name = 'bugmail/bugmail_stats.html'

    def get_context_data(self, **kwargs):
        context = super(BugmailStatsView, self).get_context_data(**kwargs)
        two_wks_ago = (now() - timedelta(days=14)).date()
        stats = BugmailStat.objects.stats_for_range(two_wks_ago)
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
        for d in date_range(two_wks_ago):
            d = date_to_js(d)
            all_stats['x_axis'].append(d)
            all_stats['total'].append([d, stats_total[d]])
            all_stats['used'].append([d, stats_used[d]])
        context['stats'] = json.dumps(all_stats)
        return context

import logging
from datetime import datetime

from django.conf import settings
from django.views.generic import TemplateView

import celery
import dateutil.parser

from scrum.utils import get_setting_or_env


redis_client = None
if getattr(settings, 'BROKER_URL', '').startswith('redis:'):
    redis_client = celery.current_app.backend.client
log = logging.getLogger(__name__)


class BugmailStatsView(TemplateView):
    template_name = 'bugmail/bugmail_stats.html'

    def get_context_data(self, **kwargs):
        context = super(BugmailStatsView, self).get_context_data(**kwargs)
        if redis_client:
            date_started = get_setting_or_env('STATS_COLLECTION_START_DATE',
                                              '2012-10-01')
            date_started = dateutil.parser.parse(date_started)
            days_since = (datetime.utcnow() - date_started).days
            bmail_total = int(redis_client.get('STATS:BUGMAILS:TOTAL') or 1)
            bmail_used = int(redis_client.get('STATS:BUGMAILS:USED') or 1)
            context['bugmail_stats'] = {
                'total': bmail_total,
                'used': bmail_used,
                'percent_used': "{0:.1%}".format(float(bmail_used) /
                                                 bmail_total),
                'date_started': date_started,
                'avg_mail': bmail_total / days_since,
                }
        return context

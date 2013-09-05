from cronjobs import register

from bugmail.tasks import get_bugmail_messages


@register
def get_bugmails():
    """Cron version of the periodic celery task."""
    get_bugmail_messages()

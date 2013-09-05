from cronjobs import register

from bugmail.tasks import clean_bugmail_log, get_bugmail_messages


@register
def get_bugmails():
    """Cron version of the periodic celery task."""
    get_bugmail_messages()


@register
def clean_bugmails():
    """Cron version of the periodic celery task."""
    clean_bugmail_log()

from django.core.management.base import NoArgsCommand

from bugmail.tasks import update_bugs
from bugmail.utils import get_bugmail_stdin, store_messages


class Command(NoArgsCommand):
    help = 'Process a bugmail piped to stdin'

    def handle_noargs(self, **options):
        msgs = get_bugmail_stdin()
        bugids = store_messages(msgs)
        if bugids:
            update_bugs.delay(bugids)

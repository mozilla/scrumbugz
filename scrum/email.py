from __future__ import absolute_import

import poplib
import re
from email.parser import Parser

from django.conf import settings

from scrum.models import Bug


BUG_ID_RE = re.compile(r'\[Bug (\d+)\]')


def get_messages():
    """
    Return a list of `email.message.Message` objects from the POP3 server.
    :return: list
    """
    messages = []
    p = Parser()
    c = poplib.POP3(settings.BUGMAIL_HOST)
    c.user(settings.BUGMAIL_USER)
    c.pass_(settings.BUGMAIL_PASS)
    num_messages = len(c.list()[1])
    for msgid in range(1, num_messages + 1):
        messages.append(p.parsestr('\n'.join(c.retr(msgid)[1])))
        c.dele(msgid)
    c.quit()
    return messages


def is_bugmail(msg):
    """
    Return true if the Message is from Bugzilla and we care about it.
    :param msg: email.message.Message object
    :return: bool
    """
    return msg.get('x-bugzilla-type') == 'changed'


def get_bug_id(msg):
    """
    Return the id of the bug the message is about.
    :param msg: email.message.Message object
    :return: str
    """
    m = BUG_ID_RE.search(msg['subject'])
    if m:
        return int(m.group(1))
    return None


def get_bugmail_ids():
    ids = [get_bug_id(m) for m in get_messages() if is_bugmail(m)]
    ids = [bid for bid in ids if bid]
    return Bug.objects.filter(id__in=ids).values_list('id', flat=True)

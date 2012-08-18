from __future__ import absolute_import

import poplib
import re
from email.parser import Parser

from django.conf import settings


BUG_ID_RE = re.compile(r'\[Bug (\d+)\]')


def get_messages(delete=True):
    """
    Return a list of `email.message.Message` objects from the POP3 server.
    :return: list
    """
    messages = []
    conn = poplib.POP3(settings.BUGMAIL_HOST)
    conn.user(settings.BUGMAIL_USER)
    conn.pass_(settings.BUGMAIL_PASS)
    num_messages = len(conn.list()[1])
    for msgid in range(1, num_messages + 1):
        msg_str = '\n'.join(conn.retr(msgid)[1])
        messages.append(Parser().parsestr(msg_str))
        if delete:
            conn.dele(msgid)
    conn.quit()
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


def get_bugmail_ids(delete=True):
    ids = [get_bug_id(m) for m in get_messages(delete=delete) if is_bugmail(m)]
    return [bid for bid in ids if bid]

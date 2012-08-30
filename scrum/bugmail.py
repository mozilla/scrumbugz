from __future__ import absolute_import

import logging
import poplib
import re
from email.parser import Parser

from django.conf import settings


BUG_ID_RE = re.compile(r'\[Bug (\d+)\]')
# 'admin' also comes through but is for account creation.
BUGZILLA_TYPES = (
    'new',
    'changed',
)
log = logging.getLogger(__name__)


BUG_INFO_HEADERS = (
    'x-bugzilla-'
)


def get_messages(delete=True):
    """
    Return a list of `email.message.Message` objects from the POP3 server.
    :return: list
    """
    messages = []
    conn = poplib.POP3_SSL(settings.BUGMAIL_HOST)
    conn.user(settings.BUGMAIL_USER)
    conn.pass_(settings.BUGMAIL_PASS)
    num_messages = len(conn.list()[1])
    for msgid in range(1, num_messages + 1):
        msg_str = '\n'.join(conn.retr(msgid)[1])
        msg = Parser().parsestr(msg_str)
        if is_bugmail(msg):
            messages.append(msg)
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
    return msg.get('x-bugzilla-type', None) in BUGZILLA_TYPES


def get_bug_id(subject):
    """
    Return the id of the bug the message is about.
    :param msg: email.message.Message object
    :return: str
    """
    m = BUG_ID_RE.search(subject)
    if m:
        return int(m.group(1))
    return None


def get_bugmails(delete=True):
    bugmails = {}
    for msg in get_messages(delete=delete):
        bid = get_bug_id(msg['subject'])
        if bid:
            bugmails[bid] = msg
    return bugmails


def store_bug_info(bid, msg):
    """
    If we have the bug, update some key info from the bugmail headers.
    """


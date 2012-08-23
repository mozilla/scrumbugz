from __future__ import absolute_import

import poplib
import re
from collections import defaultdict
from email.parser import Parser

from django.conf import settings


BUG_ID_RE = re.compile(r'\[Bug (\d+)\]')
BUG_PROJECT_RE = re.compile(r'[^+]+\+([^@]+)@')
# 'admin' also comes through but is for account creation.
BUGZILLA_TYPES = (
    'new',
    'changed',
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


def get_project_slug(mail_to):
    m = BUG_PROJECT_RE.match(mail_to)
    if m:
        return m.group(1)
    return None


def get_bugmails(delete=True):
    project_mails = defaultdict(list)
    for msg in get_messages(delete=delete):
        bid = get_bug_id(msg['subject'])
        slug = get_project_slug(msg['to'])
        if bid:
            project_mails[slug].append(bid)
    return project_mails

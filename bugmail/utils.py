from __future__ import absolute_import

import logging
import poplib
import re
import socket
from email.parser import Parser

from bugmail.models import BugmailStat
from scrum.models import ALL_COMPONENTS, BZProduct
from scrum.utils import get_setting_or_env


BUGMAIL_HOST = get_setting_or_env('BUGMAIL_HOST')
BUGMAIL_USER = get_setting_or_env('BUGMAIL_USER')
BUGMAIL_PASS = get_setting_or_env('BUGMAIL_PASS')
BUGMAIL_MAX_MESSAGES = get_setting_or_env('BUGMAIL_MAX_MESSAGES', 1000)
BUG_ID_RE = re.compile(r'\[Bug (\d+)\]')
BUG_SUMMARY_RE = re.compile(r'\[Bug (?:\d+)\](?: New:)? (.+)$')
# 'admin' also comes through but is for account creation.
BUGZILLA_TYPES = (
    'new',
    'changed',
)
BUGZILLA_INFO_HEADERS = (
    'product',
    'component',
    'severity',
    'status',
    'priority',
    'assigned-to',
    'target-milestone',
)
log = logging.getLogger(__name__)
socket.setdefaulttimeout(60 * 3)  # 3 min


def get_messages(delete=True, max_get=BUGMAIL_MAX_MESSAGES):
    """
    Return a list of `email.message.Message` objects from the POP3 server.
    :return: list
    """
    messages = []
    if BUGMAIL_HOST:
        try:
            conn = poplib.POP3_SSL(BUGMAIL_HOST)
            conn.user(BUGMAIL_USER)
            conn.pass_(BUGMAIL_PASS)
            num_messages = len(conn.list()[1])
            num_get = min(num_messages, max_get)
            log.debug('Getting %d bugmails', num_get)
            log_bugmails_total(num_get)
            for msgid in range(1, num_get + 1):
                msg_str = '\n'.join(conn.retr(msgid)[1])
                msg = Parser().parsestr(msg_str)
                if is_bugmail(msg) and is_interesting(msg):
                    messages.append(msg)
                if delete:
                    conn.dele(msgid)
            conn.quit()
        except poplib.error_proto:
            log.exception('Failed to get bugmails.')
            return []
    if messages:
        num_msgs = len(messages)
        log_bugmails_used(num_msgs)
        log.debug('Found %d interesting bugmails', num_msgs)
    else:
        log.debug('No interesting bugmails found')
    return messages


def is_interesting(msg):
    """
    Return true if the bug is of a product and component about which we care.
    :param msg: email.message.Message object
    :return: bool
    """
    all_products = BZProduct.objects.full_list()
    prod = msg['x-bugzilla-product']
    comp = msg['x-bugzilla-component']
    log.debug('Bugmail found with product=%s and component=%s', prod, comp)
    if prod in all_products:
        if not (comp in all_products[prod] or
                ALL_COMPONENTS in all_products[prod]):
            return False
        return True
    return False


def is_bugmail(msg):
    """
    Return true if the Message is from Bugzilla.
    :param msg: email.message.Message object
    :return: bool
    """
    return msg.get('x-bugzilla-type', None) in BUGZILLA_TYPES


def get_bug_id(msg):
    """
    Return the id of the bug the message is about.
    :param msg: email.message.Message object
    :return: int
    """
    if 'x-bugzilla-id' in msg:
        return int(msg['x-bugzilla-id'])
    m = BUG_ID_RE.search(msg['subject'])
    if m:
        return int(m.group(1))
    return None


def get_bugmails(delete=True):
    """
    Return a dict of parsed email messages keyed on bug id.
    :param delete: delete the email after fetching
    :return: dict
    """
    bugmails = {}
    for msg in get_messages(delete=delete):
        bid = get_bug_id(msg)
        if bid:
            bugmails[bid] = msg
    return bugmails


def extract_bug_info(msg):
    """
    Extract the useful info from the bugmail message and return it.
    :param msg: message
    :return: dict
    """
    info = {}
    m = BUG_SUMMARY_RE.match(msg['subject'])
    if m:
        info['summary'] = m.group(1)
    else:
        log.warning('Subject did not match: %s', msg['subject'])
    for h in BUGZILLA_INFO_HEADERS:
        val = msg.get('x-bugzilla-' + h)
        if val:
            info[h.replace('-', '_')] = val
    return info


def _log_bugmails(count, stat_type):
    if count:
        BugmailStat.objects.create(
            stat_type=stat_type,
            count=count,
        )


def log_bugmails_used(count):
    _log_bugmails(count, BugmailStat.USED)


def log_bugmails_total(count):
    _log_bugmails(count, BugmailStat.TOTAL)

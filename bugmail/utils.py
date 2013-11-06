from __future__ import absolute_import

import logging
import poplib
import re
import socket
import sys
from email.parser import Parser

from bugmail.models import BugmailStat
from scrum.models import ALL_COMPONENTS, Bug, BZProduct
from scrum.utils import get_setting_or_env


PARSER = Parser()
BUGMAIL_HOST = get_setting_or_env('BUGMAIL_HOST')
BUGMAIL_USER = get_setting_or_env('BUGMAIL_USER')
BUGMAIL_PASS = get_setting_or_env('BUGMAIL_PASS')
BUGMAIL_MAX_MESSAGES = get_setting_or_env('BUGMAIL_MAX_MESSAGES', 1000)
BUG_ID_RE = re.compile(r'\[Bug\s+(\d+)\]')
BUG_SUMMARY_RE = re.compile(r'{0}(?:\s+New:)?\s+(.+)$'.format(BUG_ID_RE))
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
            for msgid in range(1, num_get + 1):
                msg_str = '\n'.join(conn.retr(msgid)[1])
                msg = PARSER.parsestr(msg_str, headersonly=True)
                messages.append(msg)
                if delete:
                    conn.dele(msgid)
            conn.quit()
        except poplib.error_proto:
            log.exception('Failed to get bugmails.')
    return messages


def parse_bugmail(message):
    """
    Return a dict of interesting parsed email message from the provided email object.
    :return: dict
    """
    bugmails = {}
    for msg in process_messages(message):
        bid = get_bug_id(msg)
        if bid:
            bugmails[bid] = msg
            log.debug('Got bug {0} on stdin.'.format(bid))
    return bugmails


def get_bugmail_stdin():
    """
    Return a dict of a parsed email message from stdin keyed on bug id.
    :return: dict
    """
    message = PARSER.parse(sys.stdin, headersonly=True)
    log.debug('Got mail on stdin: ' + message['subject'])
    return parse_bugmail(message)


def get_bugmail_str(email):
    """
    Return a dict of a parsed email message from given string keyed on bug id.
    :return: dict
    """
    message = PARSER.parsestr(email, headersonly=True)
    return parse_bugmail(message)


def process_messages(msgs):
    if not isinstance(msgs, list):
        msgs = [msgs]
    log_bugmails_total(len(msgs))
    messages = [msg for msg in msgs if is_interesting(msg)]
    if messages:
        num_msgs = len(messages)
        log_bugmails_used(num_msgs)
        log.debug('Found %d interesting bugmails', num_msgs)
    else:
        log.debug('No interesting bugmails found')
    return messages


def store_messages(msgs):
    if msgs:
        for bid, msg in msgs.iteritems():
            bug_data = extract_bug_info(msg)
            bug, created = Bug.objects.get_or_create(id=bid, defaults=bug_data)
            if not created:
                for attr, val in bug_data.items():
                    setattr(bug, attr, val)
                bug.save()
        bugids = msgs.keys()
        log.info('Synced %d bug(s) from email', len(bugids))
        return bugids

    return []


def is_interesting(msg):
    """
    Return true if the bug is of a product and component about which we care.
    :param msg: email.message.Message object
    :return: bool
    """
    if not is_bugmail(msg):
        return False
    changed_fields = msg['x-bugzilla-changed-fields'].strip()
    if not changed_fields:  # just a comment
        return False
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
    messages = get_messages(delete=delete)
    for msg in process_messages(messages):
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

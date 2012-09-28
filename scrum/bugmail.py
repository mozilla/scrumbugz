from __future__ import absolute_import

import logging
import poplib
import re
from email.parser import Parser

import celery

from scrum.models import BZProduct
from scrum.utils import get_setting_or_env

try:
    import newrelic.agent
except ImportError:
    newrelic = False


redis_client = celery.current_app.backend.client

BUGMAIL_HOST = get_setting_or_env('BUGMAIL_HOST')
BUGMAIL_USER = get_setting_or_env('BUGMAIL_USER')
BUGMAIL_PASS = get_setting_or_env('BUGMAIL_PASS')
BUG_ID_RE = re.compile(r'\[Bug (\d+)\]')
BUG_SUMMARY_RE = re.compile(r'[^\]]+\](?: New:)? (.+)$')
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


def get_messages(delete=True, max_get=50):
    """
    Return a list of `email.message.Message` objects from the POP3 server.
    :return: list
    """
    messages = []
    if BUGMAIL_HOST:
        conn = poplib.POP3_SSL(BUGMAIL_HOST)
        conn.user(BUGMAIL_USER)
        conn.pass_(BUGMAIL_PASS)
        num_messages = len(conn.list()[1])
        num_get = min(num_messages, max_get)
        log.debug('Getting %d bugmails', num_get)
        redis_client.incr('STATS:BUGMAILS:TOTAL', num_get)
        if newrelic:
            newrelic.agent.record_custom_metric('Custom/AllEmail', num_get)
        for msgid in range(1, num_get + 1):
            msg_str = '\n'.join(conn.retr(msgid)[1])
            msg = Parser().parsestr(msg_str)
            if is_bugmail(msg):
                if is_interesting(msg):
                    messages.append(msg)
                if delete:
                    conn.dele(msgid)
        conn.quit()
    if messages:
        num_msgs = len(messages)
        redis_client.incr('STATS:BUGMAILS:USED', num_msgs)
        log.debug('Found %d interesting bugmails', num_msgs)
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
        if all_products[prod] and comp not in all_products[prod]:
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

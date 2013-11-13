from django.conf import settings
from django.utils.encoding import force_unicode
from django.utils.timezone import now as django_now

from jingo import helpers
from jingo import register
from jinja2.runtime import Undefined
from markdown import markdown as parse_markdown


@register.function
def bugzilla_url(bug_id):
    return '%sid=%s' % (settings.BUGZILLA_SHOW_URL, bug_id)

@register.function
def buzilla_attachment_url(attachment_id):
    return '%sid=%s' % (settings.BUGZILLA_ATTACHMENT_URL, attachment_id)

@register.filter
def markdown(value):
    return parse_markdown(
        force_unicode(value),
        extensions=settings.MARKDOWN_EXTENSIONS,
        output_format='html5',
        safe_mode=True,
    )

@register.function
def now(fmt=None):
    return helpers.datetime(django_now(), fmt)


# from http://j.mp/TIi5SQ
@register.filter
def pluralize(value, s1='s', s2=None):
    """Like Django's pluralize-filter, but instead of using an optional
    comma to separate singular and plural suffixes, it uses two distinct
    parameters.

    It also is less forgiving if applied to values that do not allow
    making a decision between singular and plural.
    """
    if s2 is not None:
        singular_suffix, plural_suffix = s1, s2
    else:
        plural_suffix = s1
        singular_suffix = ''

    try:
        if int(value) != 1:
            return plural_suffix
    except TypeError:  # not a string or a number; maybe it's a list?
        if len(value) != 1:
            return plural_suffix
    return singular_suffix


@register.filter
def timesince(value, *arg):
    if value is None or isinstance(value, Undefined):
        return u''
    from django.utils.timesince import timesince
    return timesince(value, *arg)


@register.filter
def timeuntil(value, *args):
    if value is None or isinstance(value, Undefined):
        return u''
    from django.utils.timesince import timeuntil
    return timeuntil(value, *args)

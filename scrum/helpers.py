from datetime import datetime

from jingo import helpers
from jingo import register
from jinja2.runtime import Undefined


@register.function
def now(fmt=None):
    return helpers.datetime(datetime.now(), fmt)


# from https://github.com/coffin/coffin/blob/master/coffin/template/defaultfilters.py#L72
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

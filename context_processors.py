from django.conf import settings


def context_settings(request):
    """Add whatever settings to the context"""
    cxt = {}
    for setting in getattr(settings, 'CONTEXT_SETTINGS', []):
        try:
            cxt[setting] = getattr(settings, setting)
        except AttributeError:
            continue
    return cxt

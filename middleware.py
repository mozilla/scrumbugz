from django.conf import settings
from django.http import HttpResponsePermanentRedirect

class EnforceHostnameMiddleware(object):
    """
    Enforce the hostname per the ENFORCE_HOSTNAME setting in the project's settings

    The ENFORCE_HOSTNAME can either be a single host or a list of acceptable hosts
    """
    def process_request(self, request):
        """Enforce the host name"""
        allowed_hosts = getattr(settings, 'ENFORCE_HOSTNAME', None)
        secure_only = getattr(settings, 'ENFORCE_SSL', False)

        if settings.DEBUG or not allowed_hosts:
            return None

        host = request.get_host()

        # find the allowed host name(s)
        if isinstance(allowed_hosts, basestring):
            allowed_hosts = [allowed_hosts]

        if host in allowed_hosts and (not secure_only or (secure_only and request.is_secure())):
            return None

        # redirect to the proper host name\
        new_url = "%s://%s%s" % (
            'https' if secure_only or request.is_secure() else 'http',
            allowed_hosts[0], request.get_full_path())

        return HttpResponsePermanentRedirect(new_url)

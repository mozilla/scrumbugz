from django_pylibmc.memcached import PyLibMCCache


class PyLibMCCacheFix(PyLibMCCache):

    def _get_memcache_timeout(self, timeout):
        """
        Special case timeout=0 to allow for infinite timeouts.
        """
        if timeout == 0:
            return timeout
        else:
            return super(PyLibMCCacheFix, self)._get_memcache_timeout(timeout)

from urllib2 import unquote

from django.db import models


BZ_URL_EXCLUDE = (
    'cmdtype',
    'remaction',
    'list_id',
    'columnlist',
)


class Sprint(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    bz_url = models.URLField(verbose_name='Bugzilla URL')

    def get_bz_args(self):
        """Return a dict of the arguments from the bz_url"""
        bz_url = unquote(self.bz_url)
        bz_args = bz_url.split('?')[1].split(';')
        bz_args = [arg.split('=') for arg in bz_args]
        bz_args_final = {}
        for key, val in bz_args:
            if key in BZ_URL_EXCLUDE:
                continue
            if key in bz_args_final:
                try:
                    bz_args_final[key].append(val)
                except AttributeError:
                    bz_args_final[key] = [bz_args_final[key], val]
            else:
                bz_args_final[key] = val

        return bz_args_final

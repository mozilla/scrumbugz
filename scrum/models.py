from collections import defaultdict
from datetime import datetime
from urllib2 import unquote

from django.conf import settings
from django.db import models

import slumber


BZ_URL_EXCLUDE = (
    'cmdtype',
    'remaction',
    'list_id',
    'columnlist',
)
BZ_FIELDS = (
    'id',
    'status',
    'summary',
    'history',
    'url',
    'whiteboard',
)
BZAPI = slumber.API(settings.BZ_API_URL)


class Project(models.Model):
    name = models.CharField(max_length=200)


class Sprint(models.Model):
    project = models.ForeignKey(Project, related_name='sprints')
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    created_date = models.DateTimeField(editable=False, default=datetime.now)
    bz_url = models.URLField(verbose_name='Bugzilla URL')

    class Meta:
        get_latest_by = 'created_date'
        ordering = ['-created_date']

    def _get_bz_args(self):
        """Return a dict of the arguments from the bz_url"""
        if not hasattr(self, '_bz_args'):
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

            bz_args_final['include_fields'] = ','.join(BZ_FIELDS)
            self._bz_args = bz_args_final
        return self._bz_args

    def refresh_bugs(self):
        delattr(self, '_bugs')
        delattr(self, '_bz_args')
        delattr(self, '_bugs_data')
        return self.get_bugs()

    def get_bugs(self):
        if not hasattr(self, '_bugs'):
            data = BZAPI.bug.get(**self._get_bz_args())
            self._bugs = [Bug(b) for b in data['bugs']]
        return self._bugs

    def get_bugs_data(self):
        if not hasattr(self, '_bugs_data'):
            data = {
                'users': defaultdict(int),
                'components': defaultdict(int),
                'status': defaultdict(int),
                'total_points': 0,
            }
            for bug in self.get_bugs():
                sd = bug.scrum_data
                if sd:
                    data['users'][sd['user']] += sd['points']
                    data['components'][sd['component']] += sd['points']
                    data['status'][bug.status] += sd['points']
                    data['total_points'] += sd['points']
            self._bugs_data = data
        return self._bugs_data


class Bug(object):
    def __init__(self, data):
        for key, value in data.iteritems():
            setattr(self, key, value)

    def __getattr__(self, name):
        if name in BZ_FIELDS:
            return ''
        raise AttributeError(name)

    @property
    def scrum_data(self):
        if not hasattr(self, '_wb_dict'):
            self._wb_dict = {}
            wb = self.whiteboard.strip()
            if wb:
                data = dict((k, v) for k, v in
                            (i.split('=') for i in wb.split() if '=' in i))
                if data:
                    self._wb_dict = {
                        'points': int(data.get('p', 0)),
                        'user': data.get('u', ''),
                        'component': data.get('c', '')
                    }
        return self._wb_dict

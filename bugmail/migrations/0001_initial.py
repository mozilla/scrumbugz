# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'BugmailStat'
        db.create_table('bugmail_bugmailstat', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('stat_type', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('count', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('date', self.gf('django.db.models.fields.DateField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('bugmail', ['BugmailStat'])


    def backwards(self, orm):
        # Deleting model 'BugmailStat'
        db.delete_table('bugmail_bugmailstat')


    models = {
        'bugmail.bugmailstat': {
            'Meta': {'object_name': 'BugmailStat'},
            'count': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stat_type': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        }
    }

    complete_apps = ['bugmail']
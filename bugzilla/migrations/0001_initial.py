# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Product'
        db.create_table('bugzilla_product', (
            ('id', self.gf('django.db.models.fields.PositiveSmallIntegerField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('bugzilla', ['Product'])

        # Adding model 'Component'
        db.create_table('bugzilla_component', (
            ('id', self.gf('django.db.models.fields.PositiveSmallIntegerField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(related_name='components', to=orm['bugzilla.Product'])),
        ))
        db.send_create_signal('bugzilla', ['Component'])


    def backwards(self, orm):
        # Deleting model 'Product'
        db.delete_table('bugzilla_product')

        # Deleting model 'Component'
        db.delete_table('bugzilla_component')


    models = {
        'bugzilla.component': {
            'Meta': {'object_name': 'Component'},
            'id': ('django.db.models.fields.PositiveSmallIntegerField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'components'", 'to': "orm['bugzilla.Product']"})
        },
        'bugzilla.product': {
            'Meta': {'object_name': 'Product'},
            'id': ('django.db.models.fields.PositiveSmallIntegerField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['bugzilla']
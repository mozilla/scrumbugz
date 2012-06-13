# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'BugzillaURL'
        db.create_table('scrum_bugzillaurl', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=2048)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='urls', null=True, to=orm['scrum.Project'])),
            ('sprint', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='urls', null=True, to=orm['scrum.Sprint'])),
        ))
        db.send_create_signal('scrum', ['BugzillaURL'])


        # Changing field 'Project.slug'
        db.alter_column('scrum_project', 'slug', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50))

    def backwards(self, orm):
        # Deleting model 'BugzillaURL'
        db.delete_table('scrum_bugzillaurl')


        # Changing field 'Project.slug'
        db.alter_column('scrum_project', 'slug', self.gf('django.db.models.fields.SlugField')(max_length=50, unique=True))

    models = {
        'scrum.bugzillaurl': {
            'Meta': {'object_name': 'BugzillaURL'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'urls'", 'null': 'True', 'to': "orm['scrum.Project']"}),
            'sprint': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'urls'", 'null': 'True', 'to': "orm['scrum.Sprint']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '2048'})
        },
        'scrum.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'scrum.sprint': {
            'Meta': {'ordering': "['-start_date']", 'unique_together': "(('project', 'slug'),)", 'object_name': 'Sprint'},
            'bz_url': ('django.db.models.fields.URLField', [], {'max_length': '2048'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sprints'", 'to': "orm['scrum.Project']"}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        }
    }

    complete_apps = ['scrum']
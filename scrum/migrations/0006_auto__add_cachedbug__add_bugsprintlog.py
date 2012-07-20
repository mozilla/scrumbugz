# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CachedBug'
        db.create_table('scrum_cachedbug', (
            ('id', self.gf('django.db.models.fields.PositiveIntegerField')(primary_key=True)),
            ('history', self.gf('scrum.models.CompressedJSONField')()),
            ('last_updated', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('product', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('component', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('assigned_to', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('summary', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('priority', self.gf('django.db.models.fields.CharField')(max_length=2, blank=True)),
            ('whiteboard', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('story_user', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('story_component', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('story_points', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
            ('sprint', self.gf('django.db.models.fields.related.ForeignKey')(related_name='cached_bugs', null=True, to=orm['scrum.Sprint'])),
        ))
        db.send_create_signal('scrum', ['CachedBug'])

        # Adding model 'BugSprintLog'
        db.create_table('scrum_bugsprintlog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('bug', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sprint_actions', to=orm['scrum.CachedBug'])),
            ('sprint', self.gf('django.db.models.fields.related.ForeignKey')(related_name='bug_actions', to=orm['scrum.Sprint'])),
            ('action', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('scrum', ['BugSprintLog'])


    def backwards(self, orm):
        # Deleting model 'CachedBug'
        db.delete_table('scrum_cachedbug')

        # Deleting model 'BugSprintLog'
        db.delete_table('scrum_bugsprintlog')


    models = {
        'scrum.bugsprintlog': {
            'Meta': {'object_name': 'BugSprintLog'},
            'action': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'bug': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sprint_actions'", 'to': "orm['scrum.CachedBug']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sprint': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bug_actions'", 'to': "orm['scrum.Sprint']"})
        },
        'scrum.bugzillaurl': {
            'Meta': {'ordering': "('id',)", 'object_name': 'BugzillaURL'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'urls'", 'null': 'True', 'to': "orm['scrum.Project']"}),
            'sprint': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'urls'", 'null': 'True', 'to': "orm['scrum.Sprint']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '2048'})
        },
        'scrum.cachedbug': {
            'Meta': {'object_name': 'CachedBug'},
            'assigned_to': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'history': ('scrum.models.CompressedJSONField', [], {}),
            'id': ('django.db.models.fields.PositiveIntegerField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'priority': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'product': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'sprint': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cached_bugs'", 'null': 'True', 'to': "orm['scrum.Sprint']"}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'story_component': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'story_points': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'story_user': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'whiteboard': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        },
        'scrum.project': {
            'Meta': {'object_name': 'Project'},
            'has_backlog': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'scrum.sprint': {
            'Meta': {'ordering': "['-start_date']", 'unique_together': "(('project', 'slug'),)", 'object_name': 'Sprint'},
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

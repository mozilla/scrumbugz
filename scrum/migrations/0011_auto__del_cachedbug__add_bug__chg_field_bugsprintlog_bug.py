# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'CachedBug'
        db.delete_table('scrum_cachedbug')

        # Adding model 'Bug'
        db.create_table('scrum_bug', (
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
            ('added_manually', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('sprint', self.gf('django.db.models.fields.related.ForeignKey')(related_name='cached_bugs', null=True, on_delete=models.SET_NULL, to=orm['scrum.Sprint'])),
        ))
        db.send_create_signal('scrum', ['Bug'])


        # Changing field 'BugSprintLog.bug'
        db.alter_column('scrum_bugsprintlog', 'bug_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['scrum.Bug']))

    def backwards(self, orm):
        # Adding model 'CachedBug'
        db.create_table('scrum_cachedbug', (
            ('status', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('story_component', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('product', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('last_updated', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('story_user', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('whiteboard', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('component', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('summary', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('priority', self.gf('django.db.models.fields.CharField')(max_length=2, blank=True)),
            ('assigned_to', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('added_manually', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('sprint', self.gf('django.db.models.fields.related.ForeignKey')(related_name='cached_bugs', null=True, on_delete=models.SET_NULL, to=orm['scrum.Sprint'])),
            ('story_points', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
            ('id', self.gf('django.db.models.fields.PositiveIntegerField')(primary_key=True)),
            ('history', self.gf('scrum.models.CompressedJSONField')()),
        ))
        db.send_create_signal('scrum', ['CachedBug'])

        # Deleting model 'Bug'
        db.delete_table('scrum_bug')


        # Changing field 'BugSprintLog.bug'
        db.alter_column('scrum_bugsprintlog', 'bug_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['scrum.CachedBug']))

    models = {
        'scrum.bug': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Bug'},
            'added_manually': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'assigned_to': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'history': ('scrum.models.CompressedJSONField', [], {}),
            'id': ('django.db.models.fields.PositiveIntegerField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'priority': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'product': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'sprint': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cached_bugs'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['scrum.Sprint']"}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'story_component': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'story_points': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'story_user': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'whiteboard': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        },
        'scrum.bugsprintlog': {
            'Meta': {'ordering': "('-timestamp',)", 'object_name': 'BugSprintLog'},
            'action': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'bug': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sprint_actions'", 'to': "orm['scrum.Bug']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manual': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sprint': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bug_actions'", 'to': "orm['scrum.Sprint']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'scrum.bugzillaurl': {
            'Meta': {'ordering': "('id',)", 'object_name': 'BugzillaURL'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'urls'", 'null': 'True', 'to': "orm['scrum.Project']"}),
            'sprint': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'urls'", 'null': 'True', 'to': "orm['scrum.Sprint']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '2048'})
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
            'bugs_data_cache': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'notes_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sprints'", 'to': "orm['scrum.Project']"}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        }
    }

    complete_apps = ['scrum']
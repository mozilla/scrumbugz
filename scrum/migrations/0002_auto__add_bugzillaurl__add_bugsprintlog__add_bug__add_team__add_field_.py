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
            ('date_synced', self.gf('django.db.models.fields.DateTimeField')(default='2000-01-01')),
            ('one_time', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('scrum', ['BugzillaURL'])

        # Adding model 'BugSprintLog'
        db.create_table('scrum_bugsprintlog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('bug', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sprint_actions', to=orm['scrum.Bug'])),
            ('sprint', self.gf('django.db.models.fields.related.ForeignKey')(related_name='bug_actions', to=orm['scrum.Sprint'])),
            ('action', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('scrum', ['BugSprintLog'])

        # Adding model 'Bug'
        db.create_table('scrum_bug', (
            ('id', self.gf('django.db.models.fields.PositiveIntegerField')(primary_key=True)),
            ('history', self.gf('scrum.models.CompressedJSONField')()),
            ('last_synced_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.utcnow)),
            ('product', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('component', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('assigned_to', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('resolution', self.gf('django.db.models.fields.CharField')(max_length=20, blank=True)),
            ('summary', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('priority', self.gf('django.db.models.fields.CharField')(max_length=2, blank=True)),
            ('whiteboard', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('blocks', self.gf('jsonfield.fields.JSONField')(blank=True)),
            ('depends_on', self.gf('jsonfield.fields.JSONField')(blank=True)),
            ('comments', self.gf('scrum.models.CompressedJSONField')(blank=True)),
            ('comments_count', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')()),
            ('last_change_time', self.gf('django.db.models.fields.DateTimeField')()),
            ('story_user', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('story_component', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('story_points', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
            ('sprint', self.gf('django.db.models.fields.related.ForeignKey')(related_name='bugs', null=True, on_delete=models.SET_NULL, to=orm['scrum.Sprint'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='bugs', null=True, on_delete=models.SET_NULL, to=orm['scrum.Project'])),
            ('backlog', self.gf('django.db.models.fields.related.ForeignKey')(related_name='backlog_bugs', null=True, on_delete=models.SET_NULL, to=orm['scrum.Project'])),
        ))
        db.send_create_signal('scrum', ['Bug'])

        # Adding model 'Team'
        db.create_table('scrum_team', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('slug', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50, db_index=True)),
        ))
        db.send_create_signal('scrum', ['Team'])

        # Adding field 'Sprint.team'
        db.add_column('scrum_sprint', 'team',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='sprints', null=True, to=orm['scrum.Team']),
                      keep_default=False)

        # Adding field 'Sprint.notes'
        db.add_column('scrum_sprint', 'notes',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'Sprint.notes_html'
        db.add_column('scrum_sprint', 'notes_html',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'Sprint.bugs_data_cache'
        db.add_column('scrum_sprint', 'bugs_data_cache',
                      self.gf('jsonfield.fields.JSONField')(null=True),
                      keep_default=False)


        # Changing field 'Sprint.bz_url'
        db.alter_column('scrum_sprint', 'bz_url', self.gf('django.db.models.fields.URLField')(max_length=2048, null=True))
        # Adding field 'Project.has_backlog'
        db.add_column('scrum_project', 'has_backlog',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Project.team'
        db.add_column('scrum_project', 'team',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='projects', null=True, to=orm['scrum.Team']),
                      keep_default=False)


        # Changing field 'Project.slug'
        db.alter_column('scrum_project', 'slug', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50))

    def backwards(self, orm):
        # Deleting model 'BugzillaURL'
        db.delete_table('scrum_bugzillaurl')

        # Deleting model 'BugSprintLog'
        db.delete_table('scrum_bugsprintlog')

        # Deleting model 'Bug'
        db.delete_table('scrum_bug')

        # Deleting model 'Team'
        db.delete_table('scrum_team')

        # Deleting field 'Sprint.team'
        db.delete_column('scrum_sprint', 'team_id')

        # Deleting field 'Sprint.notes'
        db.delete_column('scrum_sprint', 'notes')

        # Deleting field 'Sprint.notes_html'
        db.delete_column('scrum_sprint', 'notes_html')

        # Deleting field 'Sprint.bugs_data_cache'
        db.delete_column('scrum_sprint', 'bugs_data_cache')


        # User chose to not deal with backwards NULL issues for 'Sprint.bz_url'
        raise RuntimeError("Cannot reverse this migration. 'Sprint.bz_url' and its values cannot be restored.")
        # Deleting field 'Project.has_backlog'
        db.delete_column('scrum_project', 'has_backlog')

        # Deleting field 'Project.team'
        db.delete_column('scrum_project', 'team_id')


        # Changing field 'Project.slug'
        db.alter_column('scrum_project', 'slug', self.gf('django.db.models.fields.SlugField')(max_length=50, unique=True))

    models = {
        'scrum.bug': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Bug'},
            'assigned_to': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'backlog': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'backlog_bugs'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['scrum.Project']"}),
            'blocks': ('jsonfield.fields.JSONField', [], {'blank': 'True'}),
            'comments': ('scrum.models.CompressedJSONField', [], {'blank': 'True'}),
            'comments_count': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {}),
            'depends_on': ('jsonfield.fields.JSONField', [], {'blank': 'True'}),
            'history': ('scrum.models.CompressedJSONField', [], {}),
            'id': ('django.db.models.fields.PositiveIntegerField', [], {'primary_key': 'True'}),
            'last_change_time': ('django.db.models.fields.DateTimeField', [], {}),
            'last_synced_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow'}),
            'priority': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'product': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bugs'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['scrum.Project']"}),
            'resolution': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'sprint': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bugs'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['scrum.Sprint']"}),
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
            'sprint': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bug_actions'", 'to': "orm['scrum.Sprint']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'scrum.bugzillaurl': {
            'Meta': {'ordering': "('id',)", 'object_name': 'BugzillaURL'},
            'date_synced': ('django.db.models.fields.DateTimeField', [], {'default': "'2000-01-01'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'one_time': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'urls'", 'null': 'True', 'to': "orm['scrum.Project']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '2048'})
        },
        'scrum.project': {
            'Meta': {'object_name': 'Project'},
            'has_backlog': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'null': 'True', 'to': "orm['scrum.Team']"})
        },
        'scrum.sprint': {
            'Meta': {'ordering': "['-start_date']", 'unique_together': "(('project', 'slug'),)", 'object_name': 'Sprint'},
            'bugs_data_cache': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'bz_url': ('django.db.models.fields.URLField', [], {'max_length': '2048', 'null': 'True', 'blank': 'True'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'notes_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sprints'", 'to': "orm['scrum.Project']"}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sprints'", 'null': 'True', 'to': "orm['scrum.Team']"})
        },
        'scrum.team': {
            'Meta': {'object_name': 'Team'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        }
    }

    complete_apps = ['scrum']

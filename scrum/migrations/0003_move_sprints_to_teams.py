# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.conf import settings
from django.db import connection, models, transaction


cursor = connection.cursor()


class Migration(DataMigration):

    def forwards(self, orm):
        for project in orm.Project.objects.all():
            orm.Team.objects.create(
                id=project.id,
                name=project.name,
                slug=project.slug,
            )
            project.team_id = project.id
            project.save()
        for sprint in orm.Sprint.objects.all():
            sprint.team_id = sprint.project_id
            sprint.save()
        if 'postgresql' in settings.DATABASES['default']['ENGINE']:
            # reset the postgres autoincrement next value for team table.
            cursor.execute("SELECT setval('scrum_team_id_seq', (SELECT MAX(id) FROM scrum_team)+1)")
            transaction.commit_unless_managed()

    def backwards(self, orm):
        pass

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
    symmetrical = True

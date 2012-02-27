from django import forms

from scrum.models import Sprint, Project


class ProjectForm(forms.ModelForm):
    template_title = 'Project'
    class Meta:
        model = Project


class SprintForm(forms.ModelForm):
    template_title = 'Sprint'
    class Meta:
        model = Sprint
        fields = (
            'name',
            'slug',
            'start_date',
            'end_date',
            'bz_url',
        )

    def clean_bz_url(self):
        url = self.cleaned_data['bz_url']
        if not url.startswith('https://bugzilla.mozilla.org/buglist.cgi?'):
            raise forms.ValidationError('Must be a valid bugzilla.mozilla.org URL.')
        return url

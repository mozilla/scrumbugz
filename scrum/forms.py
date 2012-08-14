from django.core.exceptions import ValidationError
from django.core.validators import validate_comma_separated_integer_list

import floppyforms as forms

from scrum.models import BugzillaURL, Project, Sprint, Team


def validate_bzurl(url):
    if not url.startswith('https://bugzilla.mozilla.org/buglist.cgi?'):
        raise ValidationError('Must be a valid bugzilla.mozilla.org '
                                    'URL.')
    if 'cmdtype' in url or 'namedcmd' in url:
        raise ValidationError('Cannot use named commands or saved '
                                    'searches.')


class BZURLField(forms.URLField):
    def __init__(self, *args, **kwargs):
        super(BZURLField, self).__init__(*args, **kwargs)
        if self.label is None:
            self.label = u'Bugzilla URL'
        self.widget = forms.URLInput(attrs={
            'placeholder': 'https://bugzilla.mozilla.org/...',
        })
        self.validators.append(validate_bzurl)


date5 = forms.DateInput(attrs={
    'placeholder': 'YYYY-MM-DD',
})


class SlugInput(forms.TextInput):

    def get_context_data(self):
        self.attrs['pattern'] = "[-.\w]+"
        return super(SlugInput, self).get_context_data()


class ProjectForm(forms.ModelForm):
    template_title = 'Project'

    class Meta:
        model = Project
        widgets = {
            'slug': SlugInput,
        }
        fields = (
            'name',
            'slug',
            'team',
        )


class SprintForm(forms.ModelForm):
    template_title = 'Sprint'

    class Meta:
        model = Sprint
        widgets = {
            'name': forms.TextInput,
            'slug': SlugInput,
            'start_date': date5,
            'end_date': date5,
            'notes': forms.Textarea(attrs={
                'class': 'span5',
            }),
        }
        fields = (
            'name',
            'slug',
            'start_date',
            'end_date',
            'notes',
            'team',
        )


class TeamForm(forms.ModelForm):

    class Meta:
        model = Team
        fields = (
            'name',
            'slug',
        )


class SprintBugsForm(forms.ModelForm):
    new_bugs = forms.CharField(
        widget=forms.HiddenInput,
        validators=[validate_comma_separated_integer_list],
    )

    class Meta:
        model = Sprint
        fields = ('new_bugs',)

    def clean_new_bugs(self):
        new_bugs = self.cleaned_data['new_bugs']
        bugs_list = []
        if new_bugs:
            bugs_list = [int(b) for b in new_bugs.split(',')]
        return bugs_list

    def save(self, commit=True):
        new_bugs = self.cleaned_data['new_bugs']
        self.instance.update_bugs(new_bugs)
        self.instance._clear_bugs_data_cache()
        return self.instance


class ProjectBugsForm(SprintBugsForm):
    class Meta:
        model = Project
        fields = ('new_bugs',)


class CreateFormMixin(forms.ModelForm):
    url = BZURLField(required=False)

    def save(self, commit=True):
        obj = super(CreateFormMixin, self).save(commit)
        if commit:
            self.add_url(obj)
        return obj

    def add_url(self, obj):
        if self.cleaned_data['url']:
            obj.urls.create(url=self.cleaned_data['url'])


class CreateProjectForm(CreateFormMixin, ProjectForm):
    """Form for creating new projects."""


class CreateTeamForm(forms.ModelForm):

    class Meta:
        model = Team
        fields = (
            'name',
            'slug',
        )


class BZURLForm(forms.ModelForm):
    url = BZURLField()

    class Meta:
        model = BugzillaURL
        fields = (
            'url',
        )

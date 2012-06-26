import floppyforms as forms

from scrum.models import BugzillaURL, Project, Sprint


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
            'has_backlog',
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
        }
        fields = (
            'name',
            'slug',
            'start_date',
            'end_date',
        )


class BZURLForm(forms.ModelForm):
    class Meta:
        model = BugzillaURL
        widgets = {
            'url': forms.URLInput(attrs={
                'placeholder': 'https://bugzilla.mozilla.org/...',
            }),
        }
        fields = (
            'url',
        )

    def clean_url(self):
        url = self.cleaned_data['url']
        if not url.startswith('https://bugzilla.mozilla.org/buglist.cgi?'):
            raise forms.ValidationError('Must be a valid bugzilla.mozilla.org '
                                        'URL.')
        if 'cmdtype' in url or 'namedcmd' in url:
            raise forms.ValidationError('Cannot use named commands or saved '
                                        'searches.')
        return url

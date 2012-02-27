import floppyforms as forms

from scrum.models import Sprint, Project


class ProjectForm(forms.ModelForm):
    template_title = 'Project'
    class Meta:
        model = Project


date5 = forms.DateInput(attrs={
    'placeholder': 'YYYY-MM-DD',
})


class SlugInput(forms.TextInput):

    def get_context_data(self):
        self.attrs['pattern'] = "[-.\w]+"
        return super(SlugInput, self).get_context_data()


class SprintForm(forms.ModelForm):
    template_title = 'Sprint'

    class Meta:
        model = Sprint
        widgets = {
            'name': forms.TextInput,
            'slug': SlugInput,
            'start_date': date5,
            'end_date': date5,
            'bz_url': forms.URLInput,
        }
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

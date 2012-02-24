from django import forms

from scrum.models import Sprint


class BZUrlMixin(object):
    def clean_bz_url(self):
        url = self.cleaned_data['bz_url']
        if not url.startswith('https://bugzilla.mozilla.org/buglist.cgi?'):
            raise forms.ValidationError('Must be a valid bugzilla.mozilla.org URL.')
        return url


class BZUrlForm(forms.Form, BZUrlMixin):
    bz_url = forms.URLField(label='Bugzilla URL')


class SprintForm(forms.ModelForm, BZUrlMixin):
    class Meta:
        model = Sprint
        fields = (
            'name',
            'slug',
            'start_date',
            'end_date',
            'bz_url',
        )

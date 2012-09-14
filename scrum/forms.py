from django.core.exceptions import ValidationError
from django.core.validators import validate_comma_separated_integer_list

import floppyforms as forms

from scrum.models import Project, Sprint, Team, BZProduct


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


class CreateProjectForm(ProjectForm):
    """Form for creating new projects."""
    product = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Bugzilla Product/Component',
        }),
        help_text=('Select the "__ALL__" component '
                   'to include the entire Product.'),
    )

    def clean_product(self):
        prod = self.cleaned_data['product']
        if prod and '/' not in prod:
            raise ValidationError('Must be in the form "product/component"')
        return prod

    def save(self, commit=True):
        obj = super(CreateProjectForm, self).save(commit)
        if commit:
            self.add_product(obj)
        return obj

    def add_product(self, obj):
        prod = self.cleaned_data['product']
        if prod:
            prod, comp = prod.split('/', 1)
            kwargs = {'name': prod, 'project': obj}
            if comp != '__ALL__':
                kwargs['component'] = comp
            obj.products.create(**kwargs)


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


class CreateTeamForm(forms.ModelForm):

    class Meta:
        model = Team
        fields = (
            'name',
            'slug',
        )


class BZProductForm(forms.ModelForm):

    class Meta:
        model = BZProduct
        fields = (
            'name',
            'component',
            'project',
        )

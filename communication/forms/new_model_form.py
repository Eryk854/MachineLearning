from django import forms

class NewModelForm(forms.Form):

    # model_name = forms.CharField()
    # description = forms.CharField(required=False)
    # output_variable = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        CHOICES = kwargs.pop('variables') or None
        super(NewModelForm, self).__init__(*args, **kwargs)
        self.fields['model_name'] = forms.CharField(required=False)
        self.fields['description'] = forms.CharField(required=False)
        self.fields['output_name'] = forms.ChoiceField(choices=CHOICES)
        self.fields['input_fields'] = forms.MultipleChoiceField(choices=CHOICES, widget=forms.CheckboxSelectMultiple)
        self.fields['output_name'].initial = CHOICES[len(CHOICES)-1][0]




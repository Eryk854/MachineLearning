from django import forms

class NewModelForm(forms.Form):
    model_name = forms.CharField()


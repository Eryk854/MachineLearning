from django import forms

from communication.models import Dataset

class NewDatasetForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['dataset_name', 'upload_file']


from django import forms
from communication.models import BatchPrediciton


class BatchPredictionForm(forms.ModelForm):
    class Meta:
        model = BatchPrediciton
        fields = ['prediction_name', 'upload_file']


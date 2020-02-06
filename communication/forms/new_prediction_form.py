from django import forms


class NewPredictionForm(forms.Form):

    def __init__(self, *args,**kwargs):
        input_fields = kwargs.pop('input_data') or None
        print(input_fields)
        super(NewPredictionForm, self).__init__(*args, **kwargs)
        self.fields['prediction_name'] = forms.CharField(required=False)
        for input in input_fields:
            # our input_fields witch contains type and name of input
            if input[1] == "double": self.fields[input[0]] = forms.FloatField()
            elif input[1].startswith('int'): self.fields[input[0]] = forms.IntegerField()
            elif input[1].startswith('string'): self.fields[input[0]] = forms.ChoiceField(choices=input[3])
            #elif input[1] == "string": name = forms.CharField()


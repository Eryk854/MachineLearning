from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, reverse
import requests
from django.views.generic.list import ListView
from django.views.generic import TemplateView, View
from django.views.generic.edit import FormView
from django.views.generic.detail import DetailView
from .forms import NewPredictionForm, NewDatasetForm, NewModelForm, BatchPredictionForm
from django.core.exceptions import ValidationError
import time
from django.contrib import messages
from .models import Dataset, BatchPrediciton, BatchPredicitonOutut
import csv
from django.conf import settings
from django.core.files.storage import default_storage
import json
import os
import pandas as pd
from io import StringIO

def index(request):
    return render(request, "communication/main_page.html")


class MakeDatasetView(FormView):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    template_name = 'communication/make_dataset.html'
    form_class = NewDatasetForm
    success_url = '/datasets_list/'

    def form_valid(self, form):

        cleaned_data = form.cleaned_data
        # We save  our file and it's name to our databse. We need to do this to use our resource file
        new_dataset = Dataset(upload_file=cleaned_data['upload_file'], dataset_name=cleaned_data['dataset_name'])
        # basic chceck if csv file is correct
        new_dataset.save()
        dataset_path = new_dataset.upload_file.path
        if self._basic_chceck_dataset(dataset_path):
            # first we make resource and then dataset
            source_id = self._add_resource(cleaned_data['dataset_name'], dataset_path)
            self._make_dataset(cleaned_data['dataset_name'], source_id)
            return super().form_valid(form)
        else:
            messages.warning(self.request, "Your csv file is wrong. Check number of headings and data")
            return redirect('make dataset')

    def _basic_chceck_dataset(self, dataset_path):
        """This function check if the number od variables in the header matches the given value. We have to chceck this
        because it leads to a wrong dataset creation"""
        with open(dataset_path, newline='') as f:
            reader = csv.reader(f)
            return True if len(next(reader)) == len(next(reader)) else False

    def _add_resource(self, file_name, file):
        """Make BigML resource using csv file"""
        files = {file_name: open(file, 'rb')}
        data = {'name': file_name}
        r = requests.post("https://bigml.io/andromeda/source?", params=self.BIGML_AUTH, files=files, data=data)
        return r.json()['resource']

    def _make_dataset(self,file_name, source_id):

        headers = {"content-type": "application/json"}
        data = {"name": file_name, "source": source_id}
        r = requests.post("https://bigml.io/andromeda/dataset", params=self.BIGML_AUTH, json=data, headers=headers)


class MakeModelView(FormView):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    template_name = "communication/make_model.html"
    form_class = NewModelForm
    success_url = "/models_list/"

    def get(self, request, *args, **kwargs):
        names = self._take_headers(**kwargs)
        print(names)
        form = NewModelForm(variables=names)
        return render(request, "communication/make_model.html", context={'form': form,
                                                                         'dataset_id': kwargs['dataset_id']})

    def post(self, request, *args, **kwargs):
        names = self._take_headers(**kwargs)
        print(names)
        form = self.form_class(request.POST, variables=names)
        if form.is_valid():
            print(form.cleaned_data)
            self._make_model(self.kwargs['dataset_id'], form.cleaned_data)
            return HttpResponseRedirect(self.get_success_url())
        return HttpResponseRedirect('make model')

    def _take_headers(self, **kwargs):
        r = requests.get("https://bigml.io/andromeda/dataset/{}?".format(self.kwargs['dataset_id']),
                         params=self.BIGML_AUTH)
        fields = r.json()['fields']
        names = [(field, fields[field]['name']) for field in fields]
        return names

    def _make_model(self, dataset_id, input_data):

        headers = {"content-type": "application/json"}
        data = {"name": input_data['model_name'],
                'description': input_data['description'],
                'dataset': 'dataset/'+dataset_id,
                'objective_field':input_data['output_name'],
                'input_fields': input_data['input_fields']}
        r = requests.post("https://bigml.io/andromeda/model?", json=data, headers=headers, params=self.BIGML_AUTH)


class MakePredictionClass(View):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    template_name = "communication/make_prediction.html"
    form_class = [NewPredictionForm, BatchPredictionForm]

    def get(self, request, *args, **kwargs):
        """Get function creates and display two prediction form. One for single prediction and second for batch
        prediction"""

        input_fields = self._get_models_input_name(kwargs['model_name'])
        prediction_form = NewPredictionForm(input_data=input_fields)
        batch_form = BatchPredictionForm()
        first_row = ''
        for input in input_fields:
            first_row += input[0] + ','
        first_row = first_row[:-1]
        return render(request, self.template_name, context={'batch_form': batch_form,
                                                            'prediction_form': prediction_form,
                                                            'model_name': kwargs['model_name'],
                                                            'number_of_input_fields': len(input_fields),
                                                            'first_row': first_row,
                                                            'input_fields': input_fields})

    def post(self, request, **kwargs):
        """POST function needs must handle two forms. First is to make prediction from input data and second
        from csv file."""
        if 'create_single_prediction' in request.POST:
            # User wants to create single prediction
            input_fields = self._get_models_input_name(kwargs['model_name'])
            form = NewPredictionForm(request.POST, input_data=input_fields)

            if form.is_valid():
                model_name = kwargs['model_name']
                data = form.cleaned_data
                self.__make_prediction(model_name, data, input_fields)
                return redirect("prediction list")

        elif 'create_batch_prediction' in request.POST:
            # User want to send csv file and make prediction.
            form = BatchPredictionForm(request.POST, request.FILES)
            if form.is_valid():
                model_name = kwargs['model_name']
                data = form.cleaned_data
                input_fields = self._get_models_input_name(kwargs['model_name'])

                if self._check_csv_file(request.FILES['upload_file'], input_fields):
                    form.save()  # here we save our csv file in media root and in database.
                    resource_id = self._make_batch_prediction(model_name, data)
                    messages.success(self.request, "You made prediction successfully")
                    return redirect("batch prediction detail", batch_prediction_id=resource_id[16:])

        return redirect("make prediction", model_name=kwargs['model_name'])

    #                                  functions  for make single prediction
    def __make_prediction(self, model, input_data, input_fields):
        """Function wich make prediction on model and input data. It also register it and api"""
        headers = {"content-type": "application/json"}
        name = input_data['prediction_name']
        input_dataa = {}
        i = 0
        for key in input_data:
            if key !='prediction_name':
                input_dataa.update({input_fields[i][2]: input_data[key]})
                i += 1
        print(input_dataa)

        data = {'model': 'model/'+model,
                'input_data': input_dataa,
                'name': name}

        r = requests.post("https://bigml.io/andromeda/prediction?", json=data, headers=headers, params=self.BIGML_AUTH)

    def _get_models_input_name(self, model_name):
        """This function returns an array of array where is name of input field, their datatype, id of input field
        and if the input field is categorical make tuple of choices or leaves empty string."""
        r = requests.get('https://bigml.io/andromeda/model/{}?'.format(model_name), params=self.BIGML_AUTH)
        ids = r.json()['input_fields']
        model_fields = r.json()['model']['fields']
        input_fields = [[model_fields[field]['name'], model_fields[field]['datatype'], field, ''] for field in ids]
        for input in input_fields:
            if input[1] == 'string':
                input[3] = [(categorie[0], categorie[0]) for categorie in model_fields[input[2]]['summary']['categories']]
        #print(input_fields)
        return input_fields
    #                                     end single prediction
    #                                     functions for make batch prediction

    def _check_csv_file(self, csv_file, input_fields):
        # first we have to convert byte file to data frame
        s = str(csv_file.read(), 'utf-8')
        data = StringIO(s)
        df = pd.read_csv(data)

        header_list = df.columns.values
        column_types = df.dtypes
        i = 0
        for input_column in input_fields:
            if input_column[1] == "string":
                # in this column we have to deal with categorical value
                unique_df_value = df[header_list[i]].unique()
                print(unique_df_value)
                allowed_values = [value[0] for value in input_column[3]]
                for value in unique_df_value:
                    if value not in allowed_values:
                        messages.error(self.request, "It's sth wrong with your {} column. Make sure there are only \
                        allowed categorical value".format(header_list[i]))
                        return False
            else:
                # We have numerical value
                if column_types[i] not in ['int8', 'float', 'int32', 'int64']:
                    messages.error(self.request, "It's sth wrong with your {} column. Make sure that there\
                     is only numerical values".format(header_list[i]))
                    return False
            i += 1
        return True

    def _make_batch_prediction(self, model_id, data):
        """We make batch prediction using import csv file, Model_id is model on wich we make prediction and data is a
        dictionary of our form data. (there is a file and prediction name)"""

        # to make batch prediction we need to make dataset
        new_batch_predciton = BatchPrediciton(upload_file=data['upload_file'], prediction_name=data['prediction_name'])
        new_batch_predciton.save()

        source_id = self._add_resource(new_batch_predciton.upload_file.path)
        time.sleep(2)
        dataset_id = self._make_dataset(source_id)
        time.sleep(2)
        params = self.BIGML_AUTH
        headers = {'content-type': 'application/json'}
        data = {'model': "model/"+model_id, 'dataset': dataset_id, "output_dataset": True}
        r = requests.post("https://bigml.io/andromeda/batchprediction?", params=params, headers=headers, json=data)
        time.sleep(2)
        return r.json()['resource']

    def _add_resource(self, file):
        """Make BigML resource using csv file"""
        files = {'prediction': open(file, 'rb')}
        r = requests.post("https://bigml.io/andromeda/source?", params=self.BIGML_AUTH, files=files)
        return r.json()['resource']

    def _make_dataset(self, source_id):
        headers = {"content-type": "application/json"}
        data = {"source": source_id}
        r = requests.post("https://bigml.io/andromeda/dataset", params=self.BIGML_AUTH, json=data, headers=headers)
        return r.json()['resource']
    #                                  end batch prediction


class PredictionDetailView(TemplateView):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    template_name = "communication/prediction_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        prediction_id = kwargs['prediction_id']
        r = requests.get('https://bigml.io/andromeda/prediction/{}?'.format(prediction_id), params=self.BIGML_AUTH)
        context['name'] = r.json()['name']
        context['output'] = r.json()['output']
        context['prediction_id'] = prediction_id
        context['last_updated'] = PredictionDetailView._change_date_format(r.json()['updated'])
        context['input_values'] = PredictionDetailView._take_prediction_input_values(prediction_id)
        return context

    @staticmethod
    def _take_prediction_input_values(prediction_id):
        r = requests.get('https://bigml.io/andromeda/prediction/{}?'.format(prediction_id), params=PredictionListView.BIGML_AUTH)
        keys = [r.json()['fields'][input]['name'] for input in r.json()['fields']]
        input_values = {key: r.json()['input_data'][value] for key, value in zip(keys, r.json()['input_data'])}
        return input_values

    @staticmethod
    def _change_date_format(date):
        """This function change date format. We want to display only format yyyy-mm-dd hh-mm-ss """
        return date[:10] + ' ' + date[11:19]


class BatchPredictionDetailView(TemplateView):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    template_name = "communication/batch_prediction_detail.html"

    def get_context_data(self, **kwargs):
        # first we have to take our batch prediction
        context = super().get_context_data(**kwargs)
        r = requests.get('https://bigml.io/andromeda/batchprediction/{}'.format(kwargs['batch_prediction_id']), params=self.BIGML_AUTH)

        context['name'] = r.json()['name']
        context['headers'], context['values'] = self._take_input_values(r.json()['dataset'])
        context['batch_prediction_id'] = kwargs['batch_prediction_id']
        outputs = self._take_output_values(r.json()["output_dataset_resource"])

        i = 0
        for output in outputs:
            context['values'][i].append(output[0])
            i += 1

        return context

    def _take_output_values(self, outut_dataset):
        """output_dataset = dataset/id"""
        r = requests.get('https://bigml.io/andromeda/{}/download?'.format(outut_dataset), params=self.BIGML_AUTH)
        r = requests.get('https://bigml.io/andromeda/{}/download?'.format(outut_dataset), params=self.BIGML_AUTH)
        r = requests.get('https://bigml.io/andromeda/{}/download?'.format(outut_dataset), params=self.BIGML_AUTH)
        media_root = settings.MEDIA_ROOT
        dataset_id = outut_dataset[9:]
        file_path = settings.MEDIA_ROOT+'\\batch_prediction_output\{}.csv'.format(dataset_id)
        print(r.content)
        f = open(file_path,'wb')
        f.write(bytes(r.content))
        f.close()

        return self._read_output_from_csv(file_path)

    def _read_output_from_csv(self, file_path):
        with open(file_path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            output_values = []
            next(csv_reader)
            for row in csv_reader:
                output_values.append(row)

        os.remove(file_path)
        return output_values



    def _take_input_values(self, dataset_id):
        r = requests.get('https://bigml.io/andromeda/{}?'.format(dataset_id), params=self.BIGML_AUTH)
        source_id = r.json()['source']
        r = requests.get('https://bigml.io/andromeda/{}?'.format(source_id), params=self.BIGML_AUTH)

        headers = [r.json()['fields'][field]['name'] for field in r.json()['fields']]
        values = [[value for value in r.json()['fields_preview'][field]] for field in r.json()['fields_preview']]
        values = [[value[i] for value in values] for i in range(len(values[0]))]

        return headers, values

    @staticmethod
    def _take_prediction_input_values(prediction_id):
        r = requests.get('https://bigml.io/andromeda/prediction/{}?'.format(prediction_id),
                         params=PredictionListView.BIGML_AUTH)
        keys = [r.json()['fields'][input]['name'] for input in r.json()['fields']]
        input_values = {key: r.json()['input_data'][value] for key, value in zip(keys, r.json()['input_data'])}
        return input_values

    @staticmethod
    def _change_date_format(date):
        """This function change date format. We want to display only format yyyy-mm-dd hh-mm-ss """
        return date[:10] + ' ' + date[11:19]


class ModelDetailView(TemplateView):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    template_name = 'communication/model_detail.html'

    def get_context_data(self, **kwargs):
        context = super(ModelDetailView, self).get_context_data()
        r = requests.get('https://bigml.io/andromeda/model/{}'.format(kwargs['model_id']), params=self.BIGML_AUTH)
        fields = r.json()['model']['fields']
        inputs = r.json()['input_fields']
        root_children = r.json()['model']['root']['objective_summary']['categories']
        context = {'fields': [(fields[input]['optype'], fields[input]['name']) for input in inputs], # fields is a list
                   #  of tuples (type of input variable, name of variable)
                   'rows': r.json()['max_rows'],
                   'description': r.json()['description'],
                   'name': r.json()['name'],
                   'dataset_id': r.json()['dataset'],
                   'output_field': r.json()['objective_field_name'],
                   'output_summary': root_children,
                   'model_id': kwargs['model_id']}

        return context


class ModelsListView(TemplateView):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    template_name = 'communication/models_list.html'

    def get_context_data(self, **kwargs):
        """Function that creates context of all user models and send it to appropriate template """
        context = super().get_context_data(**kwargs)
        r = requests.get('https://bigml.io/andromeda/model?', params=self.BIGML_AUTH)
        objects = r.json()['objects']
        list=[]
        for obj in objects:
            element = {'resource': obj['resource'], 'name': obj['name'],  # resource is a model code
                       'updated': obj['updated']}
            list.append(element)
        context['models'] = list
        return context


class PredictionListView(TemplateView):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    template_name = 'communication/prediction_list.html'

    def get_context_data(self, **kwargs):
        """Function that creates context of all user predictions and send it to appropriate template """
        context = super().get_context_data(**kwargs)
        # We must present the parameters as text
        params = (self.BIGML_AUTH, 'order_by=model;', 'order_by=-updated;')
        text = ''
        for element in params:
            text += str(element)

        r = requests.get('https://bigml.io/andromeda/prediction?', params=text)
        objects = r.json()['objects']
        predict_list = []
        used_models = []
        models_list = []
        for obj in objects:
            element = {'model':obj['model'], 'name': obj['name'], 'prediction': obj['resource'],
                       'output': obj['output'], 'updated': PredictionListView._change_date_format(obj['updated'])}
                       #'predict_values': PredictionListView.__take_prediction_input_values(obj['resource'])}

            if element['model'] not in used_models:
                models_list = PredictionListView._take_info_about_model(element['model'], models_list)
                used_models.append(element['model'])

            predict_list.append(element)

        # We want also to write batch predictions,
        context['batch_predictions'] = PredictionListView._take_batch_predictions()
        context['predictions'] = predict_list
        context['models'] = models_list
        return context

    @staticmethod
    def _take_batch_predictions():
        r = requests.get('https://bigml.io/andromeda/batchprediction?', params=PredictionListView.BIGML_AUTH)
        batch_predictions = []
        for prediction in r.json()['objects']:
            batch_predictions.append({'name':prediction['name'],
                                      'updated': PredictionListView._change_date_format(prediction['updated']),
                                      'model': prediction['model'],
                                      'resource': prediction['resource'],
                                      'rows': prediction['rows']})
        return batch_predictions


    @staticmethod
    def _take_info_about_model(model_id, model_list):
        r = requests.get('https://bigml.io/andromeda/{}?'.format(model_id), params=PredictionListView.BIGML_AUTH)
        model_list.append({'model_id': r.json()['resource'], 'description': r.json()['description'], 'name': r.json()['name']})
        return model_list


    @staticmethod
    def _change_date_format(date):
        """This function change date format. We want to display only format yyyy-mm-dd hh-mm-ss """
        return date[:10]+' '+date[11:19]

    # @staticmethod
    # def __take_prediction_input_values(prediction):
    #     r = requests.get('https://bigml.io/andromeda/{}?'.format(prediction), params=PredictionListView.BIGML_AUTH)
    #     keys = [r.json()['fields'][input]['name'] for input in r.json()['fields']]
    #     input_values = {key: r.json()['input_data'][value] for key, value in zip(keys, r.json()['input_data'])}
    #     return input_values


class DatasetListView(TemplateView):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    template_name = 'communication/datasets_list.html'

    def get_context_data(self, **kwargs):
        """Function that creates context of all user datasets and send it to appropriate template """
        context = super().get_context_data(**kwargs)
        r = requests.get('https://bigml.io/andromeda/dataset?', params=self.BIGML_AUTH)
        objects = r.json()['objects']
        list=[]
        for obj in objects:
            # Resource is a id of the dataset. This is needed to create the model on this dataset.
            element = {'created': DatasetListView._change_date_format(obj['created']),
                       'name': obj['name'],
                       'resource': obj['resource']}
            list.append(element)
        context['datasets'] = list
        return context

    @staticmethod
    def _change_date_format(date):
        """This function change date format. We want to display only format yyyy-mm-dd hh-mm-ss """
        return date[:10] + ' ' + date[11:19]


class DeletePredictionView(View):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'

    def get(self, request, *args, **kwargs):
        r = requests.delete("https://bigml.io/andromeda/prediction/{}".format(self.kwargs['prediction_id']), params=self.BIGML_AUTH)
        print(r.status_code)
        if r.status_code == 204:
            messages.success(self.request, "You deleted the predictions successfully")
        else:
            messages.warning(self.request, "Faild to delete the prediction. Try again later")
        return redirect('prediction list')


class DeleteDatasetView(View):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'

    def get(self, request, *args, **kwargs):
        r = requests.delete("https://bigml.io/andromeda/dataset/{}".format(self.kwargs['dataset_id']), params=self.BIGML_AUTH)
        print(r.status_code)
        if r.status_code == 204:
            messages.success(self.request, "You deleted the dataset successfully")
        else:
            messages.warning(self.request, "Faild to delete the dataset. Try again later")
        return redirect('datasets list')


class DeleteModelView(View):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'

    def get(self, request, *args, **kwargs):
        r = requests.delete("https://bigml.io/andromeda/model/{}".format(self.kwargs['model_id']), params=self.BIGML_AUTH)
        print(r.status_code)
        print(r.url)
        if r.status_code == 204:
            messages.success(self.request, "You deleted the model successfully")
        else:
            messages.warning(self.request, "Faild to delete the model. Try again later")
        return redirect('models list')


class DeleteBatchPredictionView(View):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'

    def get(self, request, *args, **kwargs):
        r = requests.delete("https://bigml.io/andromeda/batchprediction/{}".format(self.kwargs['batch_prediction_id']),
                            params=self.BIGML_AUTH)
        print(r.status_code)
        if r.status_code == 204:
            messages.success(self.request, "You deleted the batch predictions successfully")
        else:
            messages.warning(self.request, "Faild to delete the batch prediction. Try again later")
        return redirect('prediction list')


def delete_prediction_confirm(request, **kwargs):
    return render(request, 'communication/delete_confirm.html',
                  context={'prediction_id': kwargs['prediction_id']})


def delete_batch_prediction_confirm(request, **kwargs):
    return render(request, 'communication/delete_confirm.html',
                  context={'batch_prediction_id': kwargs['batch_prediction_id']})


def delete_dataset_confirm(request, **kwargs):
    return render(request, 'communication/delete_confirm.html',
                  context={'dataset_id': kwargs['dataset_id']})


def delete_model_confirm(request, **kwargs):
    return render(request, 'communication/delete_confirm.html',
                  context={'model_id': kwargs['model_id']})


def _read_output_from_csv(file_path):
    with open(file_path) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        output_values = []
        headers = next(csv_reader)
        for row in csv_reader:
            output_values.append(row)

    os.remove(file_path)
    return headers, output_values


def open_dataset2(request, **kwargs):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    r = requests.get("https://bigml.io/andromeda/dataset/{}/download?".format(kwargs['dataset_id']), params=BIGML_AUTH)
    r = requests.get("https://bigml.io/andromeda/dataset/{}/download?".format(kwargs['dataset_id']), params=BIGML_AUTH)
    r = requests.get("https://bigml.io/andromeda/dataset/{}/download?".format(kwargs['dataset_id']), params=BIGML_AUTH)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="dataset.csv"'
    file_path = settings.MEDIA_ROOT + '\\dataset_details_output\{}.csv'.format(kwargs['dataset_id'])
    f = open(file_path, 'wb')
    f.write(bytes(r.content))
    f.close()

    context = _read_output_from_csv(file_path)
    return render(request,"communication/dataset.html", context={"headers": context[0],
                                                                 "values": context[1],
                                                                 "dataset_id": kwargs['dataset_id']})
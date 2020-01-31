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
from .models import Dataset
import csv
#BIGML_USERNAME = 'Eryk
#BIGML_AUTH=

def index(request):
    return render(request,"communication/main_page.html")



# należy spersonalizować zmanę nazwy zbioru  nazwę dowolnego konta różne pliki z dysku i sprawdzanie czy csv
# można dodać description czyli opis zbioru
def add_resource(request):
    """Make BigML resource using csv file"""
    bigml_auth = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    files = {'iris.csv':open('communication/diabetes.csv','rb')}
    data={'name':'Diabetes'}
    r = requests.post("https://bigml.io/andromeda/source?", params=bigml_auth, files=files, data=data)
    return HttpResponse("Add resource to server")


class MakeDatasetView(FormView):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    template_name = 'communication/make_dataset.html'
    form_class = NewDatasetForm
    success_url = '/datasets_list/'

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        # We save  our file and it's name to our databse. We need to do this to use our resource file
        new_dataset = Dataset(upload_file=cleaned_data['upload_file'], dataset_name=cleaned_data['dataset_name'])

        #basic chceck if csv file is correct
        new_dataset.save()
        dataset_path = new_dataset.upload_file.path
        if self._basic_chceck_dataset(dataset_path):
            source_id = self.__add_resource(cleaned_data['dataset_name'], dataset_path)
            self.__make_dataset(cleaned_data['dataset_name'], source_id)
            return super().form_valid(form)
        else:
            messages.warning(self.request, "Your csv file is wrong. Check number of headings and data")
            return redirect('make dataset')




    def _basic_chceck_dataset(self, dataset_path):
        with open(dataset_path, newline='') as f:
            reader = csv.reader(f)
            return True if len(next(reader)) == len(next(reader)) else False



    def __add_resource(self, file_name, file):
        """Make BigML resource using csv file"""
        files = {file_name: open(file, 'rb')}
        data = {'name': file_name}
        r = requests.post("https://bigml.io/andromeda/source?", params=self.BIGML_AUTH, files=files, data=data)
        #print(r.json())
        return r.json()['resource']

    def __make_dataset(self,file_name, source_id):

        headers = {"content-type": "application/json"}
        data = {"name":file_name, "source": source_id}
        r = requests.post("https://bigml.io/andromeda/dataset", params=self.BIGML_AUTH, json=data, headers=headers)


class MakeModelView(FormView):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    template_name = "communication/make_model.html"
    form_class = NewModelForm
    success_url = "/models_list/"
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context = {'dataset_id': self.kwargs['dataset_id'],
                   'form': self.form_class}
        return context

    def form_valid(self, form):
        self.__make_model(self.kwargs['dataset_id'], form.cleaned_data)
        return HttpResponseRedirect(self.get_success_url())

    def __make_model(self, dataset_id, input_data):

        headers = {"content-type": "application/json"}
        data = {"name": input_data['model_name'], 'description': input_data['description'], 'dataset': 'dataset/'+dataset_id}
        r = requests.post("https://bigml.io/andromeda/model?", json=data, headers=headers, params=self.BIGML_AUTH)


class MakePredictionClass(View):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    template_name = "communication/make_prediction.html"
    form_class = [NewPredictionForm, BatchPredictionForm]

    def get(self, request, *args, **kwargs):
        """Get function creates and display prediction form"""
        input_fields = self._get_models_input_name(kwargs['model_name'])
        prediction_form = NewPredictionForm(input_data=input_fields)
        batch_form = BatchPredictionForm()
        return render(request, self.template_name, context={'batch_form': batch_form,
                                                            'prediction_form': prediction_form,
                                                            'model_name': kwargs['model_name']})

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
                self.__make_prediction(model_name, data)
                return redirect("prediction list")

        elif 'create_batch_prediction' in request.POST:
            # User want to send csv file and make prediction.
            form = BatchPredictionForm(request.POST, request.FILES)
            if form.is_valid():
                model_name = kwargs['model_name']
                data = form.cleaned_data
                form.save() # here we save our csv file in media root and in database.
                self._make_batch_prediction(model_name, data)

        return redirect("make prediction", model_name=kwargs['model_name'])

    #                                  functions  for make single prediction
    def __make_prediction(self, model, input_data):
        """Function wich make prediction on model and input data. It also register it and api"""
        headers = {"content-type": "application/json"}
        name = input_data['prediction_name']
        input_dataa = {}
        i = 0
        for key in input_data:
            if key !='prediction_name':
                input_dataa.update({"00000"+str(i): input_data[key]})
            i += 1

        data = {'model': 'model/'+model,
                'input_data': input_dataa,
                'name': name}

        r = requests.post("https://bigml.io/andromeda/prediction?", json=data, headers=headers, params=self.BIGML_AUTH)

    def _get_models_input_name(self, model_name):
        """This function returns an array of tuple where is name of input field and their datatype"""
        r = requests.get('https://bigml.io/andromeda/model/{}?'.format(model_name), params=self.BIGML_AUTH)
        print(r.url)
        print(r.json())
        model_fields = r.json()['model']['model_fields']
        input_fields = [(model_fields[field]['name'], model_fields[field]['datatype']) for field in model_fields]
        return input_fields
    #                                     end single prediction
    #                                     functions for make batch prediction

    def _make_batch_prediction(self, model_id, data):
        """We make batch prediction using import csv file, Model_id is model on wich we make prediction and data is a
        dictionary of our form data. (there is a file and prediction name)"""

        # to make batch prediction we need to make dataset
        source_id = self._add_resource(data['upload_file'])
        dataset_id = self._make_dataset(source_id)
        params = self.BIGML_AUTH
        headers = {'content-type': 'application/json'}
        time.sleep(2)
        data = {'model': "model/"+model_id, 'dataset': dataset_id}
        r = requests.post("https://bigml.io/andromeda/batchprediction?", params=params, headers=headers, json=data)

    def _add_resource(self, file, data=None):
        """Make BigML resource using csv file"""
        files = {'prediction': open('media/predictions/'+str(file), 'rb')}
        #data = {'name': file_name}
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
        # firt we have to take our batch prediction
        context = super().get_context_data(**kwargs)
        r = requests.get('https://bigml.io/andromeda/batchprediction/{}'.format(kwargs['batch_prediction_id']), params=self.BIGML_AUTH)
        print(r.json())

        context['name'] = r.json()['name']
        context['input_values'] = self._take_input_values(r.json()['dataset'])

    def _take_input_values(self, dataset):
        print(dataset)


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
                                      'resource': prediction['resource']})
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
            element = {'created': obj['created'], 'name': obj['name'], 'resource': obj['resource']}
            list.append(element)
        context['datasets'] = list
        return context


class DeletePredictionView(View):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'

    def get(self, request ,*args, **kwargs):
        r = requests.delete("https://bigml.io/andromeda/prediction/{}".format(self.kwargs['prediction_id']), params=self.BIGML_AUTH)
        print(r.status_code)
        if r.status_code == 204:
            messages.success(self.request, "You deleted the predictions successfully")
        else:
            messages.warning(self.request, "Faild to delete the prediction. Try again later")
        messages.success(self.request, "You deleted the predictions successfully")
        return redirect('prediction list')


class DeleteDatasetView(View):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'

    def get(self, request ,*args, **kwargs):
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


def delete_prediction_confirm(request, **kwargs):
    return render(request, 'communication/delete_confirm.html',
                  context={'prediction_id': kwargs['prediction_id']})


def delete_dataset_confirm(request, **kwargs):
    return render(request, 'communication/delete_confirm.html',
                  context={'dataset_id': kwargs['dataset_id']})


def delete_model_confirm(request, **kwargs):
    return render(request, 'communication/delete_confirm.html',
                  context={'model_id': kwargs['model_id']})


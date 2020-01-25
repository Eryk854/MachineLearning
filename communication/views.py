from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, reverse
import requests
from django.views.generic.list import ListView
from django.views.generic import TemplateView, View
from django.views.generic.edit import FormView
from .forms import NewPredictionForm, NewDatasetForm, NewModelForm
from django.core.exceptions import ValidationError

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
    success_url = '/models_list/'

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        source_id = self.__add_resource(cleaned_data['dataset_name'], cleaned_data['upload_file'])
        self.__make_dataset(cleaned_data['dataset_name'], source_id)
        return super().form_valid(form)

    def __add_resource(self, file_name,file):
        """Make BigML resource using csv file"""
        print(file_name)
        print(file)
        files = {file_name: open('media/dataset/'+str(file), 'rb')}
        data = {'name': file_name}
        r = requests.post("https://bigml.io/andromeda/source?", params=self.BIGML_AUTH, files=files, data=data)
        return r.json()['resource']

    def __make_dataset(self,file_name, source_id):

        headers = {"content-type": "application/json"}
        data = {"name":file_name, "source": source_id}
        r = requests.post("https://bigml.io/andromeda/dataset", params=self.BIGML_AUTH, json=data, headers=headers)


def make_model(request):
    bigml_auth = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    headers = {"content-type": "application/json"}
    data={"name":"Diabetes model", 'dataset': 'dataset/5e2ae89de476845dd901b581'}
    r = requests.post("https://bigml.io/andromeda/model?",json=data, headers=headers, params=bigml_auth )
    return HttpResponse("We made model uhuuuu")


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
        self.__make_model(self.kwargs['dataset_id'], form.cleaned_data['model_name'])
        return HttpResponseRedirect(self.get_success_url())

    def __make_model(self, dataset_id, model_name):

        headers = {"content-type": "application/json"}
        data = {"name": model_name, 'dataset': 'dataset/'+dataset_id}
        r = requests.post("https://bigml.io/andromeda/model?", json=data, headers=headers, params=self.BIGML_AUTH)





class MakePredictionClass(View):
    BIGML_AUTH = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    template_name = "communication/make_prediction.html"
    form_class = NewPredictionForm

    def get(self, request, *args, **kwargs):
        """Get function creates and display prediction form"""
        input_fields = self.__get_models_input_name(kwargs['model_name'])
        form = NewPredictionForm(input_data=input_fields)
        return render(request, self.template_name, context={'form': form,
                                                            'model_name': kwargs['model_name']})

    def post(self, request, **kwargs):
        """POST function take and chceck prediction input data  and make prediction """
        input_fields = self.__get_models_input_name(kwargs['model_name'])
        form = NewPredictionForm(request.POST, input_data=input_fields)
        #data={'prediction_name':'','sepal.width':3,'petal.length':2.1 ,'petal.width':1}
        #form1 = NewPredictionForm(data, input_data=input_fields)
        #print(form.is_valid())
        #print(form.errors)
        #print(form.is_bound)
        #print(request.POST)
        #print(type(request.POST['sepal.width']))
        if form.is_valid():
            model_name = kwargs['model_name']
            data = form.cleaned_data
            print(data)
            self.__make_prediction(model_name, data)
        return redirect("make_prediction", model_name=kwargs['model_name'])

    def __make_prediction(self, model, input_data):
        """Function wich make prediction on model and input data. It also register it and api"""
        headers = {"content-type": "application/json"}
        name = input_data['prediction_name']
        input_data = zip(input_data,range(0,len(input_data)))
        input_dataa = {}
        for data, i in input_data:
            input_dataa.update({"00000"+str(i): data})

        data = {'model': 'model/'+model,
                'input_data': input_dataa,
                'name': name}
        r = requests.post("https://bigml.io/andromeda/prediction?", json=data, headers=headers, params=self.BIGML_AUTH)
        print(r.url)
        response = r.json()
        print(response)
        return HttpResponse("Predykcja się udała !")


    def __get_models_input_name(self, model_name):
        """This function returns an array of tuple where is name of input data and their datatype"""
        r = requests.get('https://bigml.io/andromeda/model/{}?'.format(model_name), params=self.BIGML_AUTH)
        model_fields = r.json()['model']['model_fields']
        input_fields = [(model_fields[field]['name'], model_fields[field]['datatype']) for field in model_fields]
        return input_fields


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
        r = requests.get('https://bigml.io/andromeda/prediction?', params=self.BIGML_AUTH)
        objects = r.json()['objects']
        list=[]
        for obj in objects:
            element = {'model':obj['model'], 'name': obj['name'], 'prediction': obj['resource'],
                       'output': obj['output'], 'updated': obj['updated']}
            list.append(element)
        context['predictions'] = list
        return context


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



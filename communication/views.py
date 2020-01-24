from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse
import requests
from django.views.generic.list import ListView
from django.views.generic import TemplateView, View
from django.views.generic.edit import FormView
from .forms import NewPredictionForm

#BIGML_USERNAME = 'Eryk
#BIGML_AUTH=


# należy spersonalizować zmanę nazwy zbioru  nazwę dowolnego konta różne pliki z dysku i sprawdzanie czy csv
# można dodać description czyli opis zbioru
def send_resource(request):
    bigml_auth = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    params = {'auth':bigml_auth}
    files = {'iris.csv':open('communication/iris.csv','rb')}
    data={'name':'testowe'}
    r = requests.post("https://bigml.io/andromeda/source?"+bigml_auth, files=files,data=data)
    print(r.url)
    return HttpResponse("Ala ma kota")


def make_dataset(request):
    
    bigml_auth = "username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;"
    headers = {"content-type": "application/json"}
    #params = {'username': bigml_auth}
    params = (bigml_auth)
    data = {"source": "source/5e2768507811dd06480055c3"}
    print("https://bigml.io/andromeda/dataset?"+bigml_auth)
    r = requests.post("https://bigml.io/andromeda/dataset", params=params, json=data,  headers=headers)
    print(r.url)
    print(r.json())
    return HttpResponse("Ala ma kota")


def make_model(request):
    bigml_auth = 'username=Eryk854;api_key=fb079f5dd95d9f28986d49f983c28a9af3cf09f9;'
    headers = {"content-type": "application/json"}
    #params = (bigml_auth)
    data={"name":"model1",'dataset': 'dataset/5e277e8be476845dd90168a6'}
    r = requests.post("https://bigml.io/andromeda/model?",json=data, headers=headers, params=bigml_auth )
    print(r.url)
    print(r.json())
    return HttpResponse("Ala ma kotaaaaa")


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

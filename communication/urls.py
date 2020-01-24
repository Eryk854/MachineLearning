from django.urls import path
from . import views

urlpatterns = [
    path('prediction_list/', views.PredictionListView.as_view(), name='prediction list'),
    path('models_list/', views.ModelsListView.as_view(), name="models list"),
    path("make_model/",views.make_model),
    path("make_prediction/model/<str:model_name>", views.MakePredictionClass.as_view(), name="make_prediction")
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="home page"),
    path('add_resource/', views.add_resource),
    path('make_dataset/', views.MakeDatasetView.as_view(), name="make dataset"),
    path('prediction_list/', views.PredictionListView.as_view(), name='prediction list'),
    path('models_list/', views.ModelsListView.as_view(), name="models list"),
    path('datasets_list/', views.DatasetListView.as_view(), name="datasets list"),
    path("make_model/dataset/<str:dataset_id>", views.MakeModelView.as_view(), name="make model"),
    path("make_prediction/model/<str:model_name>", views.MakePredictionClass.as_view(), name="make prediction"),
    path('prediction_detil/prediction/<str:prediction_id>', views.PredictionDetailView.as_view(), name="prediction detail"),
    path('delete/prediction/confirm/<str:prediction_id>', views.delete_prediction_confirm, name='delete prediction confirm'),
    path('delete/prediction/<str:prediction_id>', views.DeletePredictionView.as_view(), name="delete prediction"),

]

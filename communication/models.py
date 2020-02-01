from django.db import models
from django.core.validators import FileExtensionValidator
# Create your models here.

class Dataset(models.Model):
    upload_file = models.FileField(upload_to='dataset/',
                                   validators=[FileExtensionValidator(allowed_extensions=['csv'],
                                                                      message="Please choose the csv file")])
    dataset_name = models.CharField(max_length=100)


class BatchPrediciton(models.Model):
    upload_file = models.FileField(upload_to='predictions/',
                                   validators=[FileExtensionValidator(allowed_extensions=['csv'],
                                                                      message="Please choose the csv file")])
    prediction_name = models.CharField(max_length=100, blank=True, default='')

class BatchPredicitonOutut(models.Model):
    upload_file = models.FileField(upload_to='batch_prediction_output/')
                                   #validators=[FileExtensionValidator(allowed_extensions=['csv'],
                                   #                                   message="Please choose the csv file")])
    # @classmethod
    # def create(cls, file):




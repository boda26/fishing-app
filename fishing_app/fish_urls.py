from django.urls import path
from .views import *

urlpatterns = [
    path('catch/', FishCatchView.as_view(), name='fish_catch'),
    path('sell/', FishSellView.as_view(), name='fish_sell'),
    path('create/', FishCreateView.as_view(), name='fish_create'),
]


from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.shop_list, name='shop_list'),
    path('purchase/', views.shop_purchase, name='shop_purchase'),
]
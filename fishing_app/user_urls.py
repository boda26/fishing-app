from django.urls import path
from .views import *

urlpatterns = [
    path('is-exist/', UserExistView.as_view(), name='user_exist'),
    path('create/', CreateUserView.as_view(), name='user_create'),
    path('basic/', UserBasicView.as_view(), name='user_basic'),
    path('finance/', UserFinanceView.as_view(), name='user_finance'),
    path('level/', UserLevelView.as_view(), name='user_level'),
    path('inventory/', UserInventoryView.as_view(), name='user_inventory')
]


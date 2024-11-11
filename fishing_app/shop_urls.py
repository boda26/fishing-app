from django.urls import path
from .views import *

urlpatterns = [
    path('list/', ShopListView.as_view(), name='shop_list'),
    path('purchase/', ShopPurchaseView.as_view(), name='shop_purchase'),
    path('add-shop-item/', AddShopItemView.as_view(), name='add_shop_item'),
    path('delete-shop-item/', DeleteShopItemView.as_view(), name='delete_shop_item'),
    path('user-shopped-items/', UserShoppedItemView.as_view(), name='user_shopped_items'),
]
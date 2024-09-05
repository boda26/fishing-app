from django.urls import path
from .views import *

urlpatterns = [
    path('general/', ChatGeneralView.as_view(), name='chat_general'),
    path('command/', ChatCommandView.as_view(), name='chat_command'),
    path('draw/', ChatDrawView.as_view(), name='chat_draw'),
]

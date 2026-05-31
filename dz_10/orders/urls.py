from django.urls import path, include

from orders.views import OrderListView

app_name = 'order'

urlpatterns = [
    path('', OrderListView.as_view(), name='list'),
]
from django.urls import path

from orders.views import OrderListView

app_name = 'order'

urlpatterns = [
    path('', OrderListView.as_view(), name='list'),
]

from django.urls import path
from .views import BooksListView, BookDetailView, AddBookView

app_name = 'book'

urlpatterns = [
    path('', BooksListView.as_view(), name='list'),
    path('<int:pk>/', BookDetailView.as_view(), name='detail'),
    path('add/', AddBookView.as_view(), name='add'),
]
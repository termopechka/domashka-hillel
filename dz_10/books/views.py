from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView, DetailView, CreateView
from silk.profiling.profiler import silk_profile

from .models import Book
import logging

logger = logging.getLogger(__name__)

class BooksListView(ListView):
    model = Book
    context_object_name = 'books'
    template_name = 'books/books.html'
    paginate_by = 8

    @silk_profile(name='Book List View')
    def get(self, request, *args, **kwargs):
        logger.info(f'User {request.user.username} requested a list of books.')

        response = super().get(request, *args, **kwargs)

        return response

    def get_queryset(self):
        result = super(BooksListView, self).get_queryset()
        query = self.request.GET.get('search')
        if query:
            result = Book.objects.filter(Q(title__icontains=query) | Q(description__icontains=query))
        return result

    def get_context_data(self, **kwargs):
        context = super(BooksListView, self).get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context


class BookDetailView(DetailView):
    model = Book
    context_object_name = 'book'
    template_name = 'books/book.html'

    def get_context_data(self, **kwargs):
        context = super(BookDetailView, self).get_context_data(**kwargs)
        context['book'] = self.object
        return context


class AddBookView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Book
    permission_required = 'add_book'
    fields = ['title', 'author', 'price', 'description', 'stock', 'category']
    login_url = '/login/'
    raise_exception = True
    template_name = 'books/form_book.html'
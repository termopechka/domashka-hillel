from django.db.models import Q
from django.views.generic import TemplateView, DetailView, ListView, CreateView
from .models import Book


class IndexView(TemplateView):
    template_name = 'index.html'


class BooksListView(ListView):
    model = Book
    context_object_name = 'books'
    template_name = 'books.html'
    paginate_by = 8

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
    template_name = 'book.html'

    def get_context_data(self, **kwargs):
        context = super(BookDetailView, self).get_context_data(**kwargs)
        context['book'] = self.object
        return context


class AddBookView(CreateView):
    model = Book
    fields = ['title', 'author', 'price', 'description', 'stock', 'category']
    template_name = 'form_book.html'
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.shortcuts import render
from .models import Book
from .forms import BookForm


def index(request):
    template = loader.get_template('index.html')
    return HttpResponse(template.render({}, request))


def books(request):
    obj = Book.objects.all()
    template = loader.get_template('books.html')
    return HttpResponse(template.render({'obj': obj}, request))


def book_detail(request, book_id):
    book = Book.objects.get(id=book_id)
    template = loader.get_template('book.html')
    return HttpResponse(template.render({'book': book}, request))


def add_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = Book(
                title=form.cleaned_data['title'],
                author=form.cleaned_data['author'],
            description=form.cleaned_data['description'],
            stock=form.cleaned_data['stock'],
            category=form.cleaned_data['category'],
            )
            book.save()
            return HttpResponseRedirect('/books/')
    else:
        form = BookForm()
    return render(request, 'form_book.html', {'form': form})


def books_by_letter(request, letter):
    try:
        book = Book.objects.get(title__startswith=letter)
    except:
        return HttpResponseRedirect('/books/')
    return render(request, 'book.html', {'book': book, 'letter': letter})
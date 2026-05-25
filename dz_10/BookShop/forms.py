from django import forms

from .models import Category, Book


class BookForm(forms.ModelForm):
    title = forms.CharField(max_length=100)
    author = forms.CharField(max_length=100)
    price = forms.DecimalField(max_digits=10, decimal_places=2)
    description = forms.CharField(widget=forms.Textarea)
    stock = forms.IntegerField()
    category = forms.ModelChoiceField(queryset=Category.objects.all())

    class Meta:
        model = Book
        fields = '__all__'
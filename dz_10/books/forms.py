from django import forms

from .models import Category, Book
from orders.models import Order


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


class CheckoutForm(forms.ModelForm):
    payment_method = forms.CharField(widget=forms.HiddenInput)
    postal_code = forms.CharField(widget=forms.HiddenInput)
    country = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = Order
        fields = ['payment_method', 'postal_code', 'country']
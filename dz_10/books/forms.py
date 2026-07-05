from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Category, Book
from orders.models import Order


class BookForm(forms.ModelForm):
    title = forms.CharField(max_length=100, label=_('Title'), help_text=_('Enter the title of book'))
    author = forms.CharField(max_length=100, label=_('Author'), help_text=_('Enter the author of book'))
    price = forms.DecimalField(max_digits=10, decimal_places=2, label=_('Price'), help_text=_('Enter the price of book'))
    description = forms.CharField(widget=forms.Textarea, label=_('Description'), help_text=_('Enter the description about book'))
    stock = forms.IntegerField(label=_('Stock'))
    category = forms.ModelChoiceField(queryset=Category.objects.all(), label=_('Category'))

    class Meta:
        model = Book
        fields = '__all__'


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['shipping_address', 'city', 'postal_code', 'country', 'payment_method']
        widgets = {
            'shipping_address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'shipping_address': _('Shipping Address'),
            'city': _('City'),
            'postal_code': _('Postal Code'),
            'country': _('Country'),
            'payment_method': _('Payment Method'),
        }

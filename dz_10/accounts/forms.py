from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class MyUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username','email', 'native_name')
        labels = {
            'username': _('Username'),
            'email': _('Email address'),
            'native_name': _('Native name'),
        }
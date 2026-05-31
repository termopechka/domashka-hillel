import logging
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from silk.profiling.profiler import silk_profile

from .forms import MyUserCreationForm
from .models import User

logger = logging.getLogger(__name__)

class RegisterView(generic.CreateView):
    form_class = MyUserCreationForm
    template_name = 'register.html'
    success_url = reverse_lazy('accounts:login')

    @silk_profile(name='Register account')
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logger.info('user %s is already logged in', request.user.username)

        response = super().get(request, *args, **kwargs)

        return response
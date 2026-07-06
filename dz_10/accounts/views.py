import logging
from django.urls import reverse_lazy
from django.views import generic
from silk.profiling.profiler import silk_profile

from .forms import MyUserCreationForm

logger = logging.getLogger(__name__)


class RegisterView(generic.CreateView):
    """Create a new user account from the registration form.

    Handles:
        GET: Renders the registration form.
        POST: Validates submitted registration data and creates a user.

    Args:
        request: Django ``HttpRequest`` handled by ``CreateView``.

    Query Parameters:
        None.

    Path Parameters:
        None.

    Body:
        username (str): User login name.
        email (str): User email address.
        native_name (str): User native/display name.
        password1 (str): Password entered by the user.
        password2 (str): Confirmation password.

    Returns:
        HttpResponse: Rendered ``register.html`` with HTTP 200 for GET or
        invalid POST data.
        HttpResponseRedirect: Redirect to ``accounts:login`` after a
        successful registration.

    Permissions:
        Public endpoint. Authentication is not required.
    """

    form_class = MyUserCreationForm
    template_name = 'register.html'
    success_url = reverse_lazy('accounts:login')

    @silk_profile(name='Register account')
    def get(self, request, *args, **kwargs):
        """Render the registration form and log already-authenticated users."""
        if request.user.is_authenticated:
            logger.info('user %s is already logged in', request.user.username)

        return super().get(request, *args, **kwargs)

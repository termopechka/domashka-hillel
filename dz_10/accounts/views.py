import logging
from django.urls import reverse_lazy
from django.views import generic
from rest_framework import viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from silk.profiling.profiler import silk_profile
from .forms import MyUserCreationForm
from .models import User
from .permissions import IsOwnerOrReadOnly
from .serializer import UserSerializer

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


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
        HttpResponseRedirect: Redirect to ``auth:login`` after a
        successful registration.

    Permissions:
        Public endpoint. Authentication is not required.
    """

    form_class = MyUserCreationForm
    template_name = "register.html"
    success_url = reverse_lazy("auth:login")

    @silk_profile(name="Register account")
    def get(self, request, *args, **kwargs):
        """Render the registration form and log already-authenticated users."""
        if request.user.is_authenticated:
            logger.info("user %s is already logged in", request.user.username)

        return super().get(request, *args, **kwargs)

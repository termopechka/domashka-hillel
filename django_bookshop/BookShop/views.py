from django.http import JsonResponse
from django.views.generic import TemplateView


def health_check(request):
    """Return a lightweight liveness response for the hosting platform."""
    return JsonResponse({"status": "ok"})


class IndexView(TemplateView):
    """Render the public home page.

    Handles:
        GET: Displays the project index page.

    Args:
        request: Django ``HttpRequest`` supplied by ``TemplateView``.

    Query Parameters:
        None.

    Path Parameters:
        None.

    Body:
        None.

    Returns:
        HttpResponse: Rendered ``index.html`` template with HTTP 200.

    Permissions:
        Public endpoint. Authentication is not required.
    """

    template_name = "index.html"

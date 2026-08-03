from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView
from rest_framework import viewsets, permissions
from rest_framework.pagination import LimitOffsetPagination

from orders.models import Order
from orders.serializer import OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        result = self.queryset.select_related("user")
        query = self.request.GET.get("search")
        if query:
            result = result.filter(
                Q(user__username__icontains=query)
                | Q(user__email__icontains=query)
                | Q(status__icontains=query)
            )
        return result

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["search_query"] = self.request.GET.get("search", "")
        return context


class OrderListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Display a paginated list of orders for authorized users.

    Handles:
        GET: Renders the order list and optional search results.

    Args:
        request: Django ``HttpRequest`` handled by ``ListView``.

    Query Parameters:
        search (str, optional): Filters orders by user username, user email,
            or order status using case-insensitive contains lookups.
        page (int, optional): Page number for pagination.

    Path Parameters:
        None.

    Body:
        None.

    Returns:
        HttpResponse: Rendered ``orders.html`` with ``orders`` and
        ``search_query`` context values and HTTP 200.
        HttpResponseForbidden: HTTP 403 when an authenticated user lacks
        ``orders.view_order`` permission.

    Permissions:
        Requires authentication and ``orders.view_order`` permission. Anonymous
        users are redirected to the ``auth:login`` route.
    """

    model = Order
    template_name = "orders.html"
    context_object_name = "orders"
    permission_required = "orders.view_order"
    login_url = reverse_lazy("auth:login")
    paginate_by = 20
    raise_exception = True

    def get_queryset(self):
        result = super().get_queryset().select_related("user")
        query = self.request.GET.get("search")
        if query:
            result = result.filter(
                Q(user__username__icontains=query)
                | Q(user__email__icontains=query)
                | Q(status__icontains=query)
            )
        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        return context

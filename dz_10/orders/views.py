from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from orders.models import Order


class OrderListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Order
    template_name = 'orders.html'
    context_object_name = 'orders'
    permission_required = 'orders.view_order'
    login_url = '/login/'
    paginate_by = 20
    raise_exception = True

    def get_queryset(self):
        result = super(OrderListView, self).get_queryset()
        query = self.request.GET.get('search')
        if query:
            result = result.filter(Q(user__icontains=query) | Q(status__icontains=query))
        return result

    def get_context_data(self, **kwargs):
        context = super(OrderListView, self).get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

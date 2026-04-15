from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from ..table import get_user_table_context

@method_decorator(permission_required('auth.view_user'), name='dispatch')
class UserManagementPageView(ListView):
    model = User
    template_name = 'system/users/user.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = f'Hệ thống / <a href="{reverse("user_list")}" class="hover:underline">Người dùng</a>'
        return {**context, **get_user_table_context(self.request)}

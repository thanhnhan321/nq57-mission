from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from ..table import get_user_table_context


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('auth.view_user', raise_exception=True), name='dispatch')
class UserManagementPartialView(ListView):
    model = User
    template_name = 'system/users/user_partial.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return {**context, **get_user_table_context(self.request)}

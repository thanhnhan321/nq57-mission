from django.contrib.auth.decorators import permission_required
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from ..query import get_department_tree_context

@method_decorator(permission_required('app.view_department'), name='dispatch')
class DepartmentListView(TemplateView):
    template_name = 'system/departments/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = f'Hệ thống / <a href="{reverse("department_list")}" class="hover:underline">Đơn vị</a>'
        return {**context, **get_department_tree_context(self.request)}

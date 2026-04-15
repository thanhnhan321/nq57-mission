from django.contrib.auth.decorators import permission_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from ..query import get_department_tree_context

@method_decorator(permission_required('app.view_department'), name='dispatch')
class DepartmentListPartialView(TemplateView):
    template_name = 'system/departments/partial.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return {**context, **get_department_tree_context(self.request)}

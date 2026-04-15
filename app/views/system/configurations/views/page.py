from django.contrib.auth.decorators import permission_required
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from ..query import get_configuration_page_context

@method_decorator(permission_required('app.view_systemconfig'), name='dispatch')
class ConfigurationPageView(TemplateView):
    template_name = 'system/configurations/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = f'Hệ thống / <a href="{reverse("configuration_list")}" class="hover:underline">Cấu hình</a>'
        return {**context, **get_configuration_page_context(self.request)}

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from ..query import (
    get_configuration_tab_context,
    parse_configuration_payload,
    save_tab_values,

)
@method_decorator(permission_required('app.change_systemconfig'), name='post')
class ConfigurationPartialView(View):
    template_name = 'system/configurations/partial.html'

    def get(self, request, *args, **kwargs):
        tab_slug = (request.GET.get('tab') or '').strip() or 'mission'
        context = get_configuration_tab_context(request, tab_slug)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        tab_slug = (request.POST.get('tab') or request.GET.get('tab') or '').strip() or 'mission'
        cleaned_values, errors = parse_configuration_payload(request, tab_slug)

        if errors:
            context = get_configuration_tab_context(request, tab_slug, submitted_values=cleaned_values, errors=errors)
            return render(request, self.template_name, context, status=422)

        save_tab_values(request.user, tab_slug, cleaned_values)
        messages.success(request, 'Cập nhật cấu hình thành công')

        context = get_configuration_tab_context(request, tab_slug)
        return render(request, self.template_name, context)

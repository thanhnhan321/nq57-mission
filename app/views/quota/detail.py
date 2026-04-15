from django.core.exceptions import ViewDoesNotExist
from django.contrib.auth.decorators import permission_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from ...utils.format import format_number
from ...models import Quota

@method_decorator(permission_required('app.view_quota'), name='dispatch')
class QuotaDetailView(View):
    template_name = 'quota/detail.html'

    def get_context_data(self, **kwargs):
        id = self.request.GET.get('id', '').strip()
        display_fields = {
            'id': 'id',
            'name': 'Chỉ tiêu',
            'type': 'Cách tính',
            'department__name': 'Đơn vị chủ trì',
            'target_percent': 'Tỉ lệ được giao',
        }
        quota_dict = (
            Quota.objects.select_related('department')
            .filter(
                Q(id=id) &
                (
                    Q() if self.request.user.is_superuser else (
                        Q(department_assignments__department_id=self.request.user.profile.department_id) |
                        Q(department_id=self.request.user.profile.department_id)
                    )
                )
            )
            .values(*display_fields.keys())
            .first()
        )
        if not quota_dict:
            raise ViewDoesNotExist()

        quota_dict['target_percent'] = format_number(quota_dict['target_percent'] * 100) + '%'
        # No need to show id
        display_fields.pop('id', None)
        # Display type label instead of value
        quota_dict['type'] = Quota.Type(quota_dict['type']).label
        return {
            'quota': quota_dict,
            'fields': display_fields,
        }

    def get(self, request, *args, **kwargs):
        id = request.GET.get('id', '').strip()
        if not id:
            response = HttpResponse()
            response['HX-Redirect'] = reverse('quota_list')
            return response
        return render(request, self.template_name, self.get_context_data(**kwargs))
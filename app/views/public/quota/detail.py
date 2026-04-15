from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from ....utils.format import format_number
from ....models import Quota

class PublicQuotaDetailView(View):
    template_name = 'public/quota/detail.html'

    def get_context_data(self, **kwargs):
        id = self.request.GET.get('id', '').strip()
 
        queryset = Quota.objects.select_related('department').filter(id=id)

        display_fields = {
            'id': 'id',
            'name': 'Chỉ tiêu',
            'type': 'Cách tính',
            'department__name': 'Đơn vị chủ trì',
            'target_percent': 'Tỉ lệ được giao',
        }

        quota_dict = queryset.values(*display_fields.keys()).first()
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
            response['HX-Redirect'] = reverse('public_quota_list')
            return response
        return render(request, self.template_name, self.get_context_data(**kwargs))
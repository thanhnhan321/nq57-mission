from django.db.models import F, Q, Case, IntegerField, Sum, When
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from ....utils.format import format_number
from ....models import Quota, QuotaReport


class PublicQuotaSummaryView(View):
    template_name = 'public/quota/summary.html'

    def get_context_data(self, **kwargs):
        id = self.request.GET.get('id', '').strip()
        quota = (
            Quota.objects
            .select_related('department')
            .filter(id=id)
            .values('name', 'type', 'department__name', 'department__id', 'target_percent')
            .first()
        )
        monthly_stats = QuotaReport.objects.filter(quota_id=id)
        delta_expected = F('expected_value') - Coalesce(F('previous_report__expected_value'), 0)
        delta_actual = F('actual_value') - Coalesce(F('previous_report__actual_value'), 0)
        monthly_stats = monthly_stats.values('period__year', 'period__month').annotate(
            m_expected=Sum(delta_expected),
            m_actual=Sum(delta_actual),
            is_active=Sum(
                Case(
                    When(~Q(status__in=[QuotaReport.Status.NOT_SENT, QuotaReport.Status.REJECTED]), then=1),
                    default=0,
                    output_field=IntegerField()
                )
            )
        )
        assigned_department = 'Tất cả'
        total_expected = sum(m['m_expected'] or 0 for m in monthly_stats)
        total_actual = sum(m['m_actual'] or 0 for m in monthly_stats)
        active_months = sum(1 for m in monthly_stats if m['is_active'] > 0)
        success_months = sum(
            1 for m in monthly_stats 
            if m['m_expected'] and m['m_actual'] and m['m_actual'] >= quota['target_percent'] * m['m_expected']
        )
        total_months = len(monthly_stats)
        completion_percent = total_actual / total_expected if total_expected else 0
        quota_dict = {
            'id': id,
            'name': quota['name'],
            'type': Quota.Type(quota['type']).label,
            'lead_department_name': quota['department__name'],
            'assigned_department': assigned_department,
            'completion_percent': format_number(completion_percent * 100) + '%',
            'total_expected': total_expected,
            'total_actual': total_actual,
            'active_months': active_months,
            'success_months': success_months,
            'total_months': total_months,
        }
        fields = {
            'name': 'Chỉ tiêu',
            'type': 'Cách tính',
            'lead_department_name': 'Đơn vị chủ trì',
            'assigned_department': 'Đơn vị thực hiện',
        }
        return {
            'quota': quota_dict,
            'fields': fields,
        }

    def get(self, request, *args, **kwargs):
        id = request.GET.get('id', '').strip()
        if not id:
            response = HttpResponse()
            response['HX-Redirect'] = reverse('quota_list')
            return response
        return render(request, self.template_name, self.get_context_data(**kwargs))
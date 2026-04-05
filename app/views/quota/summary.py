from django.db.models import F, Q, Case, IntegerField, Sum, When
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from ...utils.format import format_number
from ...models import Quota, QuotaReport


class QuotaSummaryView(View):
    template_name = 'quota/summary.html'

    def get_context_data(self, **kwargs):
        id = self.request.GET.get('id', '').strip()
        quota = Quota.objects.filter(id=id, department_assignments__is_leader=True).annotate(
            lead_department_name=F('department_assignments__department__name'),
            lead_department_id=F('department_assignments__department__id'),
        ).values('name', 'lead_department_name', 'lead_department_id', 'target_percent').first()
        group_by_fields = ['month']
        monthly_stats = QuotaReport.objects.filter(quota_id=id)
        department_id = self.request.user.profile.department_id
        if self.request.user.is_superuser or quota['lead_department_id'] == department_id:
            department_id = self.request.GET.get('department_id', '').strip()
        if department_id:
            monthly_stats = monthly_stats.filter(department_id=department_id)
            group_by_fields.append('department__name')
        monthly_stats = monthly_stats.annotate(
            month=TruncMonth('created_at')
        ).values(*group_by_fields).annotate(
            m_expected=Sum('expected_value'),
            m_actual=Sum('actual_value'),
            is_active=Sum(
                Case(
                    When(~Q(status__in=[QuotaReport.Status.NOT_SENT, QuotaReport.Status.REJECTED]), then=1),
                    default=0,
                    output_field=IntegerField()
                )
            )
        )
        assigned_department = 'Tất cả'
        if department_id:
            assigned_department = monthly_stats[0]['department__name']
        total_expected = sum(m['m_expected'] or 0 for m in monthly_stats)
        total_actual = sum(m['m_actual'] or 0 for m in monthly_stats)
        active_months = sum(1 for m in monthly_stats if m['is_active'] > 0)
        success_months = sum(
            1 for m in monthly_stats 
            if m['m_expected'] and (m['m_actual'] / m['m_expected']) >= quota['target_percent']
        )
        total_months = len(monthly_stats)
        completion_percent = total_actual / total_expected if total_expected else 0
        quota_dict = {
            'id': id,
            'name': quota['name'],
            'lead_department_name': quota['lead_department_name'],
            'department_id': department_id,
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
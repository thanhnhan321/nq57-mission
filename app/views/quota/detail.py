from django.contrib.auth import PermissionDenied
from django.contrib.auth.decorators import permission_required
from django.db.models import Q, OuterRef, Subquery, Sum
from django.db.models.base import Coalesce
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from ...utils.format import format_number
from ...models import Quota, QuotaAssignment

@method_decorator(permission_required('app.view_quota'), name='dispatch')
class QuotaDetailView(View):
    template_name = 'quota/detail.html'

    def get_context_data(self, **kwargs):
        id = self.request.GET.get('id', '').strip()
        has_full_privilege = self.request.user.is_superuser
        if not has_full_privilege:
            assignment = QuotaAssignment.objects.filter(
                quota_id=id,
                department_id=self.request.user.profile.department_id,
            ).first()
            if not assignment:
                raise PermissionDenied()
            # has_full_privilege = assignment.is_leader
        # privilege_filter = Q() if has_full_privilege else Q(department_reports__department_id=self.request.user.profile.department_id)
        queryset = Quota.objects.prefetch_related('department_reports').filter(id=id)
        lead_dept_query = QuotaAssignment.objects.filter(
            quota=OuterRef('pk'),
            is_leader=True
        )
        # Lead department
        queryset = queryset.annotate(
            lead_department_name=Subquery(lead_dept_query.values('department__name')[:1]),
        )
        # Assigned departments
        # queryset = queryset.annotate(
        #     assigned_departments=StringAgg(
        #         'department_reports__department__short_name', 
        #         delimiter=', ',
        #         distinct=True
        #     )
        # )

        # Total expected and actual values
        # queryset = queryset.annotate(
        #     total_expected=Coalesce(Sum('department_reports__expected_value', filter=privilege_filter), 0),
        #     total_actual=Coalesce(Sum('department_reports__actual_value', filter=privilege_filter), 0)
        # )

        # Evaluation result
        # queryset = queryset.annotate(
        #     evaluation_result=Case(
        #         When(
        #             total_actual__gte=F('total_expected'),
        #             total_expected__gt=0,
        #             then=Value(True),
        #         ),
        #         default=Value(False),
        #         output_field=BooleanField()
        #     )
        # )

        display_fields = {
            'id': 'id',
            'name': 'Chỉ tiêu',
            'lead_department_name': 'Đơn vị chủ trì',
            # 'assigned_departments',
            'target_percent': 'Tỉ lệ được giao',
            # 'total_expected': 'Chỉ tiêu phải thực hiện',
            # 'total_actual': 'Kết quả thực hiện',
            # 'evaluation_result',
        }

        quota_dict = queryset.values(*display_fields.keys()).first()
        quota_dict['target_percent'] = format_number(quota_dict['target_percent'] * 100) + '%'
        # quota_dict['completion_percent'] = format_number(
        #     (quota_dict['total_actual'] / quota_dict['total_expected'] if quota_dict['total_expected'] else 0) * 100
        # ) + '%'
        # display_fields['completion_percent'] = 'Tỉ lệ thực hiện'
        # No need to show id
        display_fields.pop('id', None)
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
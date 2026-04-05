from django.db.models import F, Q, Case, Count, Exists, FloatField, OuterRef, Sum, When
from django.shortcuts import render
from django.views import View

from ...models import Quota, QuotaReport, Department

class QuotaPanelView(View):
    template_name = 'dashboard/quota_panel.html'

    def get(self, request, *args, **kwargs):
        year = request.GET.get('year', '').strip()
        department_id = request.GET.get('department_id', '').strip()
        quota_stats = self.get_quota_stats(year, department_id)
        # report_stats = self.get_report_stats(year, department_id)
        top_head_department_stats = self.get_department_stats(year, department_id)
        bot_head_department_stats = self.get_department_stats(year, department_id, is_descending=False)
        top_branch_department_stats = self.get_department_stats(year, department_id, type=Department.Type.CAX)
        bot_branch_department_stats = self.get_department_stats(year, department_id, type=Department.Type.CAX, is_descending=False)
        return render(
            request,
            self.template_name,
            {
                'quota_stats': quota_stats,
                'top_head_department_stats': top_head_department_stats,
                'bot_head_department_stats': bot_head_department_stats,
                'top_branch_department_stats': top_branch_department_stats,
                'bot_branch_department_stats': bot_branch_department_stats,
                'year': year,
                'department_id': department_id,
            }
        )

    def get_quota_stats(self, year, department_id):
        filter = Q()
        report_filter = Q()
        if year.isdigit():
            filter &= Exists(QuotaReport.objects.filter(quota=OuterRef('pk'), period__year=year))
            report_filter &= Q(department_reports__period__year=year)
        
        if department_id.isdigit():
            filter &= Exists(QuotaReport.objects.filter(quota=OuterRef('pk'), department_id=department_id))
            report_filter &= Q(department_reports__department_id=department_id)

        quota_query = Quota.objects.annotate(
            total_actual=Sum('department_reports__actual_value', filter=report_filter),
            total_expected=Sum('department_reports__expected_value', filter=report_filter),
        ).filter(filter)
        
        quotas = quota_query.values('id', 'total_actual', 'total_expected', 'target_percent')
        results = {
            "distinct_quota_count": 0,
            "passed_count": 0,
            "failed_count": 0,
        }

        for q in quotas:
            results["distinct_quota_count"] += 1
            actual = q['total_actual'] or 0
            expected = q['total_expected'] or 0
            target = q['target_percent']

            if expected and actual >= expected * target:
                results["passed_count"] += 1
            else:
                results["failed_count"] += 1

        return results

    def get_report_stats(self, year, department_id):
        filter = Q()
        if year.isdigit():
            filter &= Q(period__year=year)
        if department_id.isdigit():
            filter &= Q(department_id=department_id)
        
        status_query = QuotaReport.objects.filter(filter).values('status').annotate(count=Count('id'))
        status_stats = {}
        total_count = 0
        for value, _ in QuotaReport.Status.choices:
            status_stats[value + '_count'] = next((row['count'] for row in status_query if row['status'] == value), 0)
            total_count += status_stats[value + '_count']
        for value, _ in QuotaReport.Status.choices:
            status_stats[value + '_percent'] = status_stats[value + '_count'] / total_count * 100 if total_count > 0 else 0
        status_stats['total_count'] = total_count
        return status_stats

    def get_department_stats(self, year, department_id, type=Department.Type.CAP, is_descending=True):
        filter = Q(type=type)
        report_filter = Q()
        if year.isdigit():
            report_filter &= Q(quota_reports__period__year=year)
        if department_id.isdigit():
            filter &= Q(id=department_id)

        # completion_ratio := (# quotas passed) / (# quotas)
        # passed := actual_value >= expected_value * quota.target_percent (and expected_value > 0)
        passed_filter = (
            report_filter
            & Q(quota_reports__expected_value__gt=0)
            & Q(
                quota_reports__actual_value__gte=F('quota_reports__expected_value')
                * F('quota_reports__quota__target_percent')
            )
        )
        top_departments = (
            Department.objects.filter(filter)
            .annotate(
                total_quota_count=Count('quota_reports', filter=report_filter, distinct=True),
                passed_quota_count=Count('quota_reports', filter=passed_filter, distinct=True),
            )
            .annotate(
                performance_ratio=Case(
                    When(total_quota_count__gt=0, then=F('passed_quota_count') * 1.0 / F('total_quota_count')),
                    default=0.0,
                    output_field=FloatField(),
                )
            )
            .order_by(('-' if is_descending else '') + 'performance_ratio')
            .values('id', 'name', 'performance_ratio')[:3]
        )
        return top_departments
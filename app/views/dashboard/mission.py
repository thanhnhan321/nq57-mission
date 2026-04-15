from django.db.models import Q, Count, Exists, OuterRef, Subquery
from django.shortcuts import render
from django.views import View

from ...models import Mission, MissionReport
from ...handlers.directive_level import get_all_directive_levels

class MissionPanelView(View):
    template_name = 'dashboard/mission_panel.html'

    def get(self, request, *args, **kwargs):
        directive_levels = [{'value': level.id, 'label': level.description} for level in get_all_directive_levels()]
        return render(
            request,
            self.template_name,
            {
                'directive_levels': directive_levels,
            }
        )

class MissionPanelPartialView(View):
    template_name = 'dashboard/mission_panel_partial.html'
    def get(self, request, *args, **kwargs):
        directive_level_id = request.GET.get('directive_level_id', '').strip()
        year = request.GET.get('year', '').strip()
        department_id = request.GET.get('department_id', '').strip()
        report_filter = Q()
        filter = Q()
        if year.isdigit():
            report_filter &= Q(period__year=year)
            filter &= Exists(MissionReport.objects.filter(mission_id=OuterRef('pk'), period__year=year))
        if department_id.isdigit():
            filter &= Q(department_id=department_id)
        queryset = (
            Mission.objects
            .filter(directive_document__directive_level_id=directive_level_id)
            .filter(filter)
        )
        latest_report_queryset = (
            MissionReport.objects
            .filter(mission_id=OuterRef('pk'))
            .filter(report_filter)
            .order_by('-period_id')
        )
        mission_status_map = {
            f'count-{status}': Count('code', filter=Q(mission_status=status)) 
            for status in MissionReport.MissionStatus
        }
        status_map = {
            f'count-{status}': Count('code', filter=Q(report_status=status)) 
            for status in MissionReport.Status
        }
        queryset = queryset.annotate(
            mission_status=Subquery(latest_report_queryset.values('mission_status')[:1]),
            report_status=Subquery(latest_report_queryset.values('status')[:1]),
        )
        statistics = (
            queryset
            .aggregate(
                total_missions=Count('code'),
                total_departments=Count('department_id', distinct=True),
                total_submitted_departments=Count('department_id', filter=Q(report_status=MissionReport.Status.APPROVED), distinct=True),
                **mission_status_map,
                **status_map,
            )
        )
        for key in status_map.keys():
            statistics[f'{key}_ratio'] = round(
                statistics[key] / statistics['total_missions'] * 100 if statistics['total_missions'] > 0 else 0,
                2
            )
        statistics['total_submitted_departments_ratio'] = round(
            statistics['total_submitted_departments'] / statistics['total_departments'] * 100 if statistics['total_departments'] > 0 else 0,
            2
        )
        return render(
            request,
            self.template_name,
            {
                'directive_level_id': directive_level_id,
                'year': year,
                'department_id': department_id,
                'statistics': statistics,
            }
        )
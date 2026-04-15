from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import method_decorator
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from ....constants import OPTION_COLOR_CLASS_MAP
from ....utils.format import format_number
from ....models import QuotaReport, SystemConfig
from ...templates.components.button import Button
from ...templates.components.table import TableRowAction, TableContext, TableColumn
from ....handlers.period import get_quota_report_deadline
from ....handlers.config import get_config

def evaluation_result_formatter(value):
    color_map = {
        True: "green",
        False: "red",
    }
    return f'<div class="rounded-full {OPTION_COLOR_CLASS_MAP[color_map[value]]} text-xs px-2 py-1">{'Đạt' if value else 'Không đạt'}</div>'

status_label_map = dict(QuotaReport.Status.choices)
def status_formatter(value):
    klass = OPTION_COLOR_CLASS_MAP[QuotaReport.Status(value).color]
    return f'<div class="w-fit rounded-full {klass} text-xs px-2 py-1 m-1">{status_label_map[value]}</div>'

COLUMNS = [
    TableColumn(
        name='month',
        label='Kỳ báo cáo',
    ),
    TableColumn(
        name='expected_value',
        label='Chỉ tiêu phải thực hiện',
        type=TableColumn.Type.NUMBER,
    ),
    TableColumn(
        name='actual_value',
        label='Kết quả thực hiện',
        type=TableColumn.Type.NUMBER,
    ),
    TableColumn(
        name='quota__target_percent',
        label='Tỉ lệ được giao',
        type=TableColumn.Type.TEXT,
        formatter=lambda value: format_number(value*100) + '%',
    ),
    TableColumn(
        name='completion_percent',
        label='Tỉ lệ thực hiện',
        type=TableColumn.Type.TEXT,
        formatter=lambda value: format_number(value*100) + '%',
    ),
    TableColumn(
        name='evaluation_result',
        label='Đánh giá',
        type=TableColumn.Type.BOOLEAN,
        formatter=evaluation_result_formatter,
    ),
]

NON_AGGREGATED_COLUMNS = [
    TableColumn(
        name='status',
        label='Trạng thái',
        type=TableColumn.Type.TEXT,
        formatter=status_formatter,
    ),
    TableColumn(
        name='note',
        label='Ghi chú',
    ),
    TableColumn(
        name='reason',
        label='Lý do',
    ),
]
def row_actions(request):
    if not request.GET.get('department_id', '').strip().isdigit():
        return []
    return [
        TableRowAction(
            icon='eye.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.OUTLINED,
            disabled=False,
            extra_attributes={
                '@click': f'''$dispatch("modal:open", {{
                    url: "{reverse("quota_report_update", query={"id": "__ROW_ID__"})}",
                    title: "Xem báo cáo chỉ tiêu",
                    ariaLabel: "Xem báo cáo chỉ tiêu",
                }});''',
                'title': 'Xem báo cáo chỉ tiêu',
            },
            render_predicate=lambda row: not row['can_edit'],
        ),
        TableRowAction(
            icon='edit.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.OUTLINED,
            disabled=False,
            extra_attributes={
                '@click': f'''$dispatch("modal:open", {{
                    url: "{reverse("quota_report_update", query={"id": "__ROW_ID__"})}",
                    title: "Cập nhật báo cáo chỉ tiêu",
                    ariaLabel: "Cập nhật báo cáo chỉ tiêu",
                    closeEvent: "quota:success",
                }});''',
                'title': 'Cập nhật báo cáo chỉ tiêu',
            },
            render_predicate=lambda row: row['can_edit'],
        ),
    ]

def get_common_context(request):
    quota_id = request.GET.get('quota_id', '').strip()
    columns = list(COLUMNS)
    queryset = QuotaReport.objects.select_related('quota').filter(quota_id=quota_id)
    group_by_fields = ['period__year', 'period__month', 'quota__target_percent']
    department_id = request.GET.get('department_id', '').strip()
    if department_id.isdigit():
        queryset = queryset.filter(department_id=department_id)
        group_by_fields.extend(['id', 'status','note', 'reason'])
        columns.extend(NON_AGGREGATED_COLUMNS)
    
    queryset = queryset.values(*group_by_fields).annotate(
        expected_value=Sum(F('expected_value')),
        actual_value=Sum(F('actual_value')),
    ).order_by('-period_id')

    current_deadline = get_quota_report_deadline()
    cutoff_day = int(get_config(SystemConfig.Key.QUOTA_CUTOFF_DAY))
    def transformer(row):
        row['month'] = f'Tháng {row['period__month']}/{row['period__year']}'
        if row.get('status'):
            if row['status'] == QuotaReport.Status.NOT_SENT:
                row['expected_value'] = None
                row['actual_value'] = None
            report_deadline = timezone.make_aware(
                timezone.datetime(
                    row['period__year'],
                    row['period__month'] + 1,
                    cutoff_day,
                )
            )
            row['can_edit'] = row['status'] not in [QuotaReport.Status.PASSED, QuotaReport.Status.FAILED] and (
                current_deadline is None or report_deadline >= timezone.now()
            )
        row['completion_percent'] = row['actual_value'] / row['expected_value'] if row['expected_value'] and row['actual_value'] else 0
        row['evaluation_result'] = True if row['expected_value'] and row['completion_percent'] >= row['quota__target_percent'] else False
        
        return row

    table_context = TableContext(
        request=request,
        reload_event='quota:success',
        columns=columns,
        filters=[],
        partial_url=reverse('quota_report_summary_partial', query={"quota_id": quota_id, 'department_id': department_id or ''}),
        actions=[],
        row_actions=row_actions(request),
    )
    return {
        **table_context.to_response_context(queryset, transformer=transformer)
    }

@method_decorator(permission_required('app.view_quotareport'), name='dispatch')
class QuotaReportSummaryPartialView(View):
    template_name = 'quota/report/summary_partial.html'

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

    def get(self, request, *args, **kwargs):
        quota_id = request.GET.get('quota_id', '').strip()
        if not quota_id:
            response = HttpResponse()
            response['HX-Redirect'] = reverse('quota_list')
            return response
        return render(request, self.template_name, self.get_context_data(**kwargs))

@method_decorator(permission_required('app.view_quotareport'), name='dispatch')
class QuotaReportSummaryView(QuotaReportSummaryPartialView):
    template_name = 'quota/report/summary.html'
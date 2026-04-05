from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import method_decorator
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from ....constants import OPTION_COLOR_CLASS_MAP
from ....utils.format import format_number
from ....models import QuotaReport
from ...templates.components.button import Button
from ...templates.components.table import TableAction, TableRowAction, TableContext, TableColumn

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
        formatter=lambda value: value.strftime('Tháng %m/%Y'),
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
            icon='edit.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.OUTLINED,
            disabled=False,
            extra_attributes={
                '@click': f'''$dispatch("modal:open", {{
                    url: "{reverse("quota_report_update", query={"id": "__ROW_ID__"})}",
                    title: "Cập nhật báo cáo chỉ tiêu",
                    ariaLabel: "Cập nhật báo cáo chỉ tiêu",
                    closeEvent: "quota-report:success",
                }});'''
            }
        ),
    ]

def get_common_context(request):
    quota_id = request.GET.get('quota_id', '').strip()
    columns = list(COLUMNS)
    queryset = QuotaReport.objects.select_related('quota').filter(quota_id=quota_id)
    group_by_fields = ['month', 'quota__target_percent']
    department_id = request.GET.get('department_id', '').strip()
    if department_id.isdigit():
        queryset = queryset.filter(department_id=department_id)
        group_by_fields.extend(['id', 'status','note', 'reason'])
        columns.extend(NON_AGGREGATED_COLUMNS)
    
    queryset = queryset.annotate(
        month=TruncMonth('created_at')
    ).values(*group_by_fields).annotate(
        expected_value=Sum('expected_value'),
        actual_value=Sum('actual_value'),
    )

    def transformer(row):
        row['completion_percent'] = row['actual_value'] / row['expected_value'] if row['expected_value'] else 0
        row['evaluation_result'] = True if row['expected_value'] and row['completion_percent'] >= row['quota__target_percent'] else False
        return row

    table_context = TableContext(
        request=request,
        reload_event='quota-report:success',
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
class QuotaReportSummaryView(View):
    template_name = 'quota/report/summary.html'

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

    def get(self, request, *args, **kwargs):
        quota_id = request.GET.get('quota_id', '').strip()
        if not quota_id:
            response = HttpResponse()
            response['HX-Redirect'] = reverse('quota_list')
            return response
        return render(request, self.template_name, self.get_context_data(**kwargs))

class QuotaReportSummaryPartialView(QuotaReportSummaryView):
    template_name = 'quota/report/summary_partial.html'
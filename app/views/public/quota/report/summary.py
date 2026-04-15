from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from .....constants import OPTION_COLOR_CLASS_MAP
from .....utils.format import format_number
from .....models import QuotaReport
from ....templates.components.table import TableContext, TableColumn

def evaluation_result_formatter(value):
    color_map = {
        True: "green",
        False: "red",
    }
    return f'<div class="rounded-full {OPTION_COLOR_CLASS_MAP[color_map[value]]} text-xs px-2 py-1">{'Đạt' if value else 'Không đạt'}</div>'

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

def get_common_context(request):
    quota_id = request.GET.get('quota_id', '').strip()
    queryset = QuotaReport.objects.select_related('quota').filter(quota_id=quota_id)
    group_by_fields = ['period__year', 'period__month', 'quota__target_percent']
    
    queryset = queryset.values(*group_by_fields).annotate(
        expected_value=Sum(F('expected_value')),
        actual_value=Sum(F('actual_value')),
    ).order_by('-period_id')

    def transformer(row):
        row['month'] = f'Tháng {row['period__month']}/{row['period__year']}'
        row['completion_percent'] = row['actual_value'] / row['expected_value'] if row['expected_value'] and row['actual_value'] else 0
        row['evaluation_result'] = True if row['expected_value'] and row['completion_percent'] >= row['quota__target_percent'] else False
        return row

    table_context = TableContext(
        request=request,
        reload_event='quota:success',
        columns=COLUMNS,
        partial_url=reverse('public_quota_report_summary_partial', query={"quota_id": quota_id}),
    )
    return {
        **table_context.to_response_context(queryset, transformer=transformer)
    }

class PublicQuotaReportSummaryView(View):
    template_name = 'public/quota/report/summary.html'

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

    def get(self, request, *args, **kwargs):
        quota_id = request.GET.get('quota_id', '').strip()
        if not quota_id:
            response = HttpResponse()
            response['HX-Redirect'] = reverse('public_quota_list')
            return response
        return render(request, self.template_name, self.get_context_data(**kwargs))

class PublicQuotaReportSummaryPartialView(PublicQuotaReportSummaryView):
    template_name = 'public/quota/report/summary_partial.html'
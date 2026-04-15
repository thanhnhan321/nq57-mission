from django.db.models import (
    F,
    Q,
    BooleanField,
    Case,
    Count,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.urls import reverse
from django.views.generic import ListView

from .....constants import OPTION_COLOR_CLASS_MAP
from .....models import QuotaReport

from ....templates.components.table import TableContext, FilterParam, TableColumn
from .....utils.format import format_number

def evaluation_result_formatter(value):
    color_map = {
        True: "green",
        False: "red",
    }
    return f'<span class="rounded-full {OPTION_COLOR_CLASS_MAP[color_map[value]]} text-xs px-2 py-1">{'Đạt' if value else 'Không đạt'}</span>'

COLUMNS = [
    TableColumn(
        name='period',
        label='Kỳ báo cáo',
    ),
    TableColumn(
        name='department__name',
        label='Đơn vị',
    ),
    TableColumn(
        name='expected_value',
        label='Chỉ tiêu phải thực hiện',
    ),
    TableColumn(
        name='actual_value',
        label='Kết quả thực hiện',
    ),
    TableColumn(
        name='completion_percent',
        label='Tỉ lệ thực hiện',
        type=TableColumn.Type.TEXT,
        formatter=lambda value: format_number(value * 100) + '%',
    ),
    TableColumn(
        name='evaluation_result',
        label='Đánh giá',
        type=TableColumn.Type.BOOLEAN,
        formatter=evaluation_result_formatter,
    ),
    TableColumn(
        name='submit_at',
        label='Ngày gửi',
        type=TableColumn.Type.DATE,
    ),
    TableColumn(
        name='reviewed_at',
        label='Ngày đánh giá',
        type=TableColumn.Type.DATE,
    ),
    TableColumn(
        name='status',
        label='Tình trạng',
        type=TableColumn.Type.TEXT,
    ),
]

def table_filters(quota_id: int):
    return [
        FilterParam(
            name='department_id',
            label='Đơn vị',
            type=FilterParam.Type.SELECT,
            query=lambda value: Q(department_id=value),
            placeholder='Tất cả',
            extra_attributes={
                'options_url': reverse('department_options', query={"quota_id": quota_id}),
            },
        ),
        FilterParam(
            name='evaluation_result',
            label='Đánh giá',
            type=FilterParam.Type.SELECT,
            query=lambda value: Q(evaluation_result=value=="true"),
            placeholder='Tất cả',
            extra_attributes={
                'options_url': reverse('quota_evaluation_result_options'),
            },
        ),
        FilterParam(
            name='report_statuses',
            label='Tình trạng báo cáo',
            type=FilterParam.Type.MULTISELECT,
            query=lambda value: Q(status__in=value),
            placeholder='Tất cả',
            extra_attributes={
                'options_url': reverse('quota_report_status_options'),
            },
        ),
    ]

COUNT_PREFIX = 'count-'

def build_statistics_block(aggregated_stats):
    ITEM_WRAPPER_CLASS = "flex items-center gap-1.5"
    LABEL_MAP = {
        'total_departments': 'Số đơn vị',
        'total_reports': 'Số báo cáo',
        'total_expected': 'Chỉ tiêu phải thực hiện',
        'total_actual': 'Kết quả thực hiện',
        'completion_percent': 'Tỉ lệ thực hiện',
    } | {
        f'{COUNT_PREFIX}{val}': label for val, label in QuotaReport.Status.choices
    }
    def build_item(key, value, right_border):
        text_color = 'text-slate-900'
        if key.startswith(COUNT_PREFIX):
            text_color = 'text-' + QuotaReport.Status(key.rsplit(COUNT_PREFIX, 1)[-1]).color + '-500'
        return f'''
        <div class="{ITEM_WRAPPER_CLASS} {'border-r border-slate-200' if right_border else ''}">
            <span>{LABEL_MAP[key]}:</span>
            <span class="font-bold {text_color}">{value}</span>
        </div>
        '''
    items = [
        build_item(key, value, index != len(aggregated_stats) - 1) for index, (key, value) in enumerate(aggregated_stats.items())
    ]
    return f'''
    <div class="grid grid-cols-5 gap-4 bg-white py-2 px-4 text-sm text-gray-500">
        {''.join(items)}
    </div>
    '''

def get_common_context(request):
    quota_id = request.GET.get('quota_id').strip()
    
    queryset = QuotaReport.objects.filter(quota_id=quota_id)
    # Evaluation result
    queryset = queryset.annotate(
        evaluation_result=Case(
            When(
                ~Q(status=QuotaReport.Status.NOT_SENT),
                actual_value__gte=F('quota__target_percent') * F('expected_value'),
                expected_value__gt=0,
                then=Value(True),
            ),
            default=Value(False),
            output_field=BooleanField()
        )
    )
    
    status_aggs = {
        f"{COUNT_PREFIX}{val}": Count(
            'id', 
            filter=Q(status=val)
        )
        for val, _ in QuotaReport.Status.choices
    }
    def aggregate_report_statistics(stats_qs):
        base = stats_qs.aggregate(
            total_reports=Count('id'),
            total_departments=Count('department_id', distinct=True),
            **status_aggs,
        )
        totals = stats_qs.exclude(status=QuotaReport.Status.NOT_SENT).aggregate(
            total_expected=Sum(F('expected_value') - Coalesce(F('previous_report__expected_value'), 0)),
            total_actual=Sum(F('actual_value') - Coalesce(F('previous_report__actual_value'), 0)),
        )
        return {**base, **totals}

    def statistics_builder(aggregated_stats):
        if aggregated_stats['total_expected'] is None:
            aggregated_stats['total_expected'] = '-'
            aggregated_stats['completion_percent'] = '0%'
        if aggregated_stats['total_actual'] is None:
            aggregated_stats['total_actual'] = '-'
        else:
            aggregated_stats['completion_percent'] = format_number(
                aggregated_stats['total_actual'] / aggregated_stats['total_expected'] * 100
                if aggregated_stats['total_expected'] else 0
            ) + '%'
        status_statistics_set = {
            key: aggregated_stats.pop(key) for key in status_aggs.keys()
        }
        return build_statistics_block(aggregated_stats) + build_statistics_block(status_statistics_set)
    query_fields = [
        'id',
        'period__year',
        'period__month',
        'department_id',
        'department__name',
        'expected_value',
        'actual_value',
        'evaluation_result',
        'status',
        'submit_at',
        'reviewed_at',
    ]
    statistics_source_queryset = queryset
    queryset = queryset.values(*query_fields).distinct()

    def transformer(row):
        row['period'] = f'Tháng {row['period__month']}/{row['period__year']}'
        row['quota_id'] = quota_id
        if row['status'] == QuotaReport.Status.NOT_SENT:
            row['expected_value'] = None
            row['actual_value'] = None
        row['completion_percent'] = row['actual_value'] / row['expected_value'] if row['expected_value'] and row['actual_value'] else 0
        status_label_map = dict(QuotaReport.Status.choices)
        klass = OPTION_COLOR_CLASS_MAP[QuotaReport.Status(row['status']).color]
        row['status'] = f'<div class="w-fit rounded-full {klass} text-xs px-2 py-1 m-1">' + status_label_map[row['status']] + '</div>'
        return row

    table_context = TableContext(
        request=request,
        columns=COLUMNS,
        filters=table_filters(quota_id),
        partial_url=reverse('public_quota_report_list_partial', query={"quota_id": quota_id}),
        statistics_builder=statistics_builder,
    )

    return {
        **table_context.to_response_context(
            queryset,
            transformer=transformer,
            statistics_queryset=statistics_source_queryset,
            statistics_fn=aggregate_report_statistics,
        )
    }

class PublicQuotaReportListView(ListView):
    model = QuotaReport
    template_name = "public/quota/report/list.html"

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

    def get(self, request, *args, **kwargs):
        quota_id = request.GET.get('quota_id').strip()
        if not quota_id:
            response = HttpResponse()
            response['HX-Redirect'] = reverse('public_quota_list')
            return response
        return super().get(request, *args, **kwargs)

class PublicQuotaReportListPartialView(PublicQuotaReportListView):
    template_name = "public/quota/report/partial.html"
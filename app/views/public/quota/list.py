from django.db.models import (
    BigIntegerField,
    F,
    Q,
    BooleanField,
    Case,
    Count,
    OuterRef,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.views.generic import ListView

from ....constants import OPTION_COLOR_CLASS_MAP
from ....models import Quota, QuotaReport
from ...templates.components.button import Button
from ...templates.components.table import TableContext, TableRowAction, FilterParam, TableColumn
from ....utils.format import format_number

def evaluation_result_formatter(value):
    color_map = {
        True: "green",
        False: "red",
    }
    return f'<span class="rounded-full {OPTION_COLOR_CLASS_MAP[color_map[value]]} text-xs px-2 py-1">{'Đạt' if value else 'Không đạt'}</span>'

def quota_name_formatter(row):
    return f'''
    <span
    class="text-blue-500 hover:underline cursor-pointer"
    @click="$dispatch('modal:open', {{
        url: '{reverse("public_quota_detail", query={"id": row['id']})}',
        title: 'Xem chi tiết chỉ tiêu',
        ariaLabel: 'Xem chi tiết chỉ tiêu'
    }});">
    {row['name']}
    </span>'''

def quota_report_statuses_formatter(row):
    html = ''
    status_label_map = dict(QuotaReport.Status.choices)
    for status in QuotaReport.Status:
        value = row['report_statuses'][status]
        klass = OPTION_COLOR_CLASS_MAP[status.color]
        html += f'<div class="w-fit rounded-full {klass} text-xs px-2 py-1 m-1">' + format_number(value) + ' ' + status_label_map[status] + '</div>'
    return html

COLUMNS = [
    TableColumn(
        name='name',
        label='Tên chỉ tiêu',
        need_tooltip=True,
        is_hypertext=True,
        formatter=quota_name_formatter,
        align='left',
    ),
    TableColumn(
        name='department__name',
        label='Đơn vị chủ trì',
    ),
    TableColumn(
        name='target_percent',
        label='Tỉ lệ được giao',
        type=TableColumn.Type.TEXT,
        formatter=lambda value: f"{value*100:.2f}%",
    ),
    TableColumn(
        name='completion_percent',
        label='Tỉ lệ thực hiện',
        type=TableColumn.Type.TEXT,
        formatter=lambda value: f"{value*100:.2f}%",
    ),
    TableColumn(
        name='evaluation_result',
        label='Đánh giá',
        type=TableColumn.Type.BOOLEAN,
        formatter=evaluation_result_formatter,
    ),
    TableColumn(
        name='report_statuses',
        label='Tình trạng báo cáo',
        type=TableColumn.Type.TEXT,
        formatter=quota_report_statuses_formatter,
        is_hypertext=True,
    ),
]

def table_filters():
    def evaluation_result_query(value):
        if value:
            return Q(total_actual__gte=F('target_percent') * F('total_expected'))
        return Q(total_actual__isnull=True) | Q(total_actual__lt=F('target_percent') * F('total_expected'))
    return [
        FilterParam(
            name='lead_department',
            label='Đơn vị chủ trì',
            type=FilterParam.Type.SELECT,
            inner_type=FilterParam.Type.NUMBER,
            query=lambda value: Q(department_id=value),
            placeholder='Tất cả',
            extra_attributes={
                'options_url': reverse('department_options'),
            },
        ),
        FilterParam(
            name='evaluation_result',
            label='Đánh giá',
            type=FilterParam.Type.SELECT,
            inner_type=FilterParam.Type.BOOLEAN,
            query=lambda value: evaluation_result_query(value),
            placeholder='Tất cả',
            extra_attributes={
                'options_url': reverse('quota_evaluation_result_options'),
            },
        )
    ]

def row_actions():
    actions = [
        TableRowAction(
            icon='eye.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.OUTLINED,
            disabled=False,
            extra_attributes={
                '@click': f'''$dispatch("modal:open", {{
                    url: "{reverse("public_quota_detail", query={"id": "__ROW_ID__"})}",
                    title: "Xem chi tiết chỉ tiêu",
                    ariaLabel: "Xem chi tiết chỉ tiêu"
                }});''',
                'title': 'Xem chi tiết chỉ tiêu',
            }
        ),
        TableRowAction(
            icon='task.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.OUTLINED,
            disabled=False,
            extra_attributes={
                '@click': f'''$dispatch("modal:open", {{
                    url: "{reverse("public_quota_summary", query={"id": "__ROW_ID__"})}",
                    title: "Xem báo cáo chỉ tiêu",
                    ariaLabel: "Xem báo cáo chỉ tiêu"
                }});''',
                'title': 'Xem báo cáo chỉ tiêu',
            }
        ),
    ]
    return actions

COUNT_PREFIX = 'count-'


def get_common_context(request):
    queryset = Quota.objects.select_related('department')

    # Public totals follow the same rule as internal views:
    #   total = Σ(value - previous_report.value)
    def scoped_reports(quota_id_outer_ref=None):
        ref = OuterRef('pk') if quota_id_outer_ref is None else quota_id_outer_ref
        return QuotaReport.objects.filter(quota_id=ref)

    def delta_total_subquery(value_field: str, prev_value_field: str) -> Subquery:
        delta_expr = F(value_field) - Coalesce(F(prev_value_field), 0)
        return Subquery(
            scoped_reports()
            .exclude(status=QuotaReport.Status.NOT_SENT)
            .values('quota_id')
            .annotate(_s=Sum(delta_expr))
            .values('_s')[:1],
            output_field=BigIntegerField(),
        )

    report_status_annotations = {
        f'{COUNT_PREFIX}{val}': Count(
            'department_reports',
            filter=Q(department_reports__status=val),
        )
        for val, _ in QuotaReport.Status.choices
    }

    queryset = queryset.annotate(
        total_expected=delta_total_subquery('expected_value', 'previous_report__expected_value'),
        total_actual=delta_total_subquery('actual_value', 'previous_report__actual_value'),
        **report_status_annotations,
    )

    query_fields = [
        'id',
        'name',
        'target_percent',
        'department__id',
        'department__name',
        'total_expected',
        'total_actual',
    ]
    query_fields.extend(report_status_annotations.keys())

    queryset = queryset.values(*query_fields)

    def transformer(row):
        row['completion_percent'] = row['total_actual'] / row['total_expected'] if row['total_expected'] and row['total_actual'] else 0
        row['evaluation_result'] = True if row['total_expected'] and row['completion_percent'] >= row['target_percent'] else False
        row['report_statuses'] = {}
        for status in QuotaReport.Status:
            row['report_statuses'][status] = row[f'{COUNT_PREFIX}{status}']
        return row

    table_context = TableContext(
        request=request,
        columns=COLUMNS,
        filters=table_filters(),
        partial_url=reverse('public_quota_list_partial'),
        row_actions=row_actions(),
        show_ordinal=True,
    )

    return {
        **table_context.to_response_context(queryset, transformer=transformer)
    }

class PublicQuotaListView(ListView):
    model = Quota
    template_name = "public/quota/list.html"

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

class PublicQuotaListPartialView(PublicQuotaListView):
    template_name = "public/quota/partial.html"
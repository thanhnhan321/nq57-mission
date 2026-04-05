from django.db.models import F, Q, BooleanField, Case, Count, FloatField, JSONField, OuterRef, Subquery, Sum, Value, When
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import JSONObject
from django.db.models.query import Cast
from django.db.models.sql.query import RawSQL
from django.urls import reverse
from django.views.generic import ListView

from ....constants import OPTION_COLOR_CLASS_MAP
from ....models import Quota, QuotaAssignment, QuotaReport
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
        name='lead_department_name',
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
    return [
        FilterParam(
            name='lead_department',
            label='Đơn vị chủ trì',
            type=FilterParam.Type.SELECT,
            inner_type=FilterParam.Type.NUMBER,
            query=lambda value: Q(lead_department_id=value),
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
            query=lambda value: Q(evaluation_result=value),
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
                }});'''
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
                }});'''
            }
        ),
    ]
    return actions

REPORT_SUMMARY_SQL_TEMPLATE = """
(
    SELECT report_json FROM (
        -- BRANCH 1: Cumulative
        SELECT 
            jsonb_build_object(
                'total_expected', SUM(sub.expected_value),
                'total_actual', SUM(sub.actual_value),
                'reported_departments', STRING_AGG(DISTINCT sub.short_name, ', '),
                {dynamic_status_sql} -- <--- Inject dynamic counts here
            ) AS report_json
        FROM (
            SELECT DISTINCT ON (qr.department_id)
                qr.expected_value, qr.actual_value, qr.status, d.short_name
            FROM quota_report qr
            JOIN department d ON qr.department_id = d.id
            WHERE qr.quota_id = quota.id 
              AND qr.status != 'not_sent'
            ORDER BY qr.department_id, qr.period_id DESC
        ) sub
        WHERE quota.type = 'cumulative'
        HAVING COUNT(*) > 0

        UNION ALL

        -- BRANCH 2: Standard
        SELECT 
            jsonb_build_object(
                'total_expected', SUM(qr.expected_value),
                'total_actual', SUM(qr.actual_value),
                'reported_departments', STRING_AGG(DISTINCT d.short_name, ', '),
                {dynamic_status_sql} -- <--- And here
            )
        FROM quota_report qr
        JOIN department d ON qr.department_id = d.id
        WHERE quota.type != 'cumulative'
          AND qr.quota_id = quota.id
        HAVING COUNT(*) > 0
    ) r LIMIT 1
)
"""

def get_common_context(request):
    queryset = Quota.objects
    dept_queryset = QuotaAssignment.objects.filter(
        quota=OuterRef('pk'),
    )
    lead_dept_query = dept_queryset.filter(
        is_leader=True
    )
    # Lead department & assigned departments
    queryset = queryset.annotate(
        lead_department_id=Subquery(lead_dept_query.values('department_id')[:1]),
        lead_department_name=Subquery(lead_dept_query.values('department__short_name')[:1]),
    )

    COUNT_PREFIX = 'count-'
    status_sql_fragments = [
        f"'{COUNT_PREFIX}{val}', COUNT(*) FILTER (WHERE status = '{val}')"
        for val, _ in QuotaReport.Status.choices
    ]
    report_summary_sql = REPORT_SUMMARY_SQL_TEMPLATE.format(
        dynamic_status_sql=', '.join(status_sql_fragments),
    )

    
    queryset = queryset.annotate(
        report_data=RawSQL(
            report_summary_sql,
            [],
            output_field=JSONField(),
        )
    )
    queryset = queryset.alias(
        total_actual=Cast(KeyTextTransform('total_actual', 'report_data'), FloatField()),
        total_expected=Cast(KeyTextTransform('total_expected', 'report_data'), FloatField()),
    ).annotate(
        evaluation_result=Case(
            When(
                total_actual__gte=F('target_percent') * F('total_expected'),
                then=Value(True),
            ),
            default=Value(False),
            output_field=BooleanField()
        )
    )

    query_fields = [
        'id',
        'name',
        'target_percent',
        'lead_department_id',
        'lead_department_name',
        'report_data',
        'evaluation_result',
    ]

    queryset = queryset.values(*query_fields)

    def transformer(row):
        row['total_expected'] = row['report_data']['total_expected'] if row['report_data'] else None
        row['total_actual'] = row['report_data']['total_actual'] if row['report_data'] else None
        row['completion_percent'] = row['total_actual'] / row['total_expected'] if row['total_expected'] else 0
        row['report_statuses'] = {}
        for status in QuotaReport.Status:
            row['report_statuses'][status] = row['report_data'][f"{COUNT_PREFIX}{status}"] if row['report_data'] else 0
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
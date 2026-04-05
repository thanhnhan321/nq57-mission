from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import method_decorator
from django.db.models import F, Q, BooleanField, Case, Count, Exists, FloatField, OuterRef, Subquery, Sum, Value, When
from django.contrib.postgres.aggregates import StringAgg
from django.db.models.functions import JSONObject
from django.db.models.query import Cast
from django.urls import reverse
from django.views.generic import ListView

from ...constants import OPTION_COLOR_CLASS_MAP
from ...models import Period, Quota, QuotaAssignment, QuotaReport
from ..templates.components.button import Button
from ..templates.components.table import TableContext, TableAction, TableRowAction, FilterParam, TableColumn, MISSING
from ...utils.format import format_number

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
        url: '{reverse("quota_detail", query={"id": row['id']})}',
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
        align=TableColumn.Align.LEFT,
    ),
    TableColumn(
        name='lead_department_name',
        label='Đơn vị chủ trì',
    ),
    TableColumn(
        name='assigned_departments',
        label='Đơn vị thực hiện',
    ),
    TableColumn(
        name='target_percent',
        label='Tỉ lệ được giao',
        type=TableColumn.Type.TEXT,
        formatter=lambda value: f"{value*100:.2f}%",
    ),
    TableColumn(
        name='total_expected',
        label='Chỉ tiêu phải thực hiện',
        type=TableColumn.Type.NUMBER,
    ),
    TableColumn(
        name='total_actual',
        label='Kết quả thực hiện',
        type=TableColumn.Type.NUMBER,
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

def table_filters(request, **kwargs):
    year = request.GET.get('year', '')
    period_ids = MISSING
    if year:
        period_ids = [int(id) for id in Period.objects.filter(year=year).values_list('id', flat=True)]
    filters = [
        FilterParam(
            name='search',
            label='Từ khóa',
            placeholder='Tìm kiếm theo tên',
            type=FilterParam.Type.TEXT,
            query=lambda value: Q(name__icontains=value),
        ),
        FilterParam(
            name='period_ids',
            label='Kỳ báo cáo',
            placeholder='Tất cả',
            type=FilterParam.Type.MULTISELECT,
            inner_type=FilterParam.Type.NUMBER,
            value=period_ids,
            query=lambda value: Exists(QuotaReport.objects.filter(quota=OuterRef('pk'), period_id__in=value)),
            extra_attributes={
                'options_url': reverse('period_options'),
            },
        ),
        FilterParam(
            name='lead_department_id',
            label='Đơn vị chủ trì',
            type=FilterParam.Type.SELECT,
            inner_type=FilterParam.Type.NUMBER,
            query=lambda value: Q(lead_department_id=value),
            placeholder='Tất cả',
            extra_attributes={
                'options_url': reverse('department_options', query={'scope': 'lead'}),
            },
        ),
        FilterParam(
            name='assigned_department_id',
            label='Đơn vị thực hiện',
            type=FilterParam.Type.SELECT,
            inner_type=FilterParam.Type.NUMBER,
            query=lambda value: (
                Exists(QuotaReport.objects.filter(quota=OuterRef('pk'), department_id=value)) | 
                Exists(QuotaAssignment.objects.filter(quota=OuterRef('pk'), department_id=value, is_leader=False))
            ),
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
        ),
    ]
    def status_query(value):
        report_filter = Q(quota=OuterRef('pk'), status__in=value)
        if request.user.is_superuser:
            return Exists(QuotaReport.objects.filter(report_filter))
        is_leader_filter = Exists(QuotaAssignment.objects.filter(quota=OuterRef('pk'), department_id=request.user.profile.department_id, is_leader=True))
        return Exists(QuotaReport.objects.filter(report_filter & Q(department_id=request.user.profile.department_id))) | (is_leader_filter & Exists(QuotaReport.objects.filter(report_filter)))

    filters.append(
        FilterParam(
            name='report_statuses',
            label='Tình trạng báo cáo',
            type=FilterParam.Type.MULTISELECT,
            inner_type=FilterParam.Type.TEXT,
            query=status_query,
            placeholder='Tất cả',
            extra_attributes={
                'options_url': reverse('quota_report_status_options'),
            },
        )
    )
    return filters

def table_actions(request):
    actions = []
    if request.user.is_superuser:
        actions = [
            TableAction(
                label="Xuất báo cáo",
                icon="download.svg",
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.OUTLINED,
                disabled=False,
                loading_text="Đang xuất...",
                klass="!border-red-700 !bg-white !text-red-800 hover:!border-red-800 hover:!bg-red-50 hover:!text-red-900 active:!bg-red-100",
                extra_attributes={
                    "menu": {
                        "groups": [
                            [
                                {
                                    "label": "Xuất báo cáo tổng hợp theo kỳ báo cáo",
                                    "icon": "download.svg",
                                    "extra_attributes": {
                                        "@click": f"(() => {{ const baseUrl='{reverse('summary_quota_export_excel')}'; const container=$event.currentTarget.closest('[x-id]'); const form=container?.querySelector('form'); if(!form) {{ window.location=baseUrl + window.location.search; return; }} const fd=new FormData(form); const params=new URLSearchParams(); for(const [k,v] of fd.entries()) params.append(k,v); const qs=params.toString(); window.location=baseUrl + (qs ? '?' + qs : ''); }})()",
                                    },
                                },
                                {
                                    "label": "Xuất báo cáo tổng hợp theo đơn vị chủ trì",
                                    "icon": "download.svg",
                                    "extra_attributes": {
                                        "@click": f"(() => {{ const baseUrl='{reverse('summary_department_export_excel')}'; const container=$event.currentTarget.closest('[x-id]'); const form=container?.querySelector('form'); if(!form) {{ window.location=baseUrl + window.location.search; return; }} const fd=new FormData(form); const params=new URLSearchParams(); for(const [k,v] of fd.entries()) params.append(k,v); const qs=params.toString(); window.location=baseUrl + (qs ? '?' + qs : ''); }})()",
                                    },
                                },
                                # {
                                #     "label": "Xuất báo cáo tổng hợp",
                                #     "icon": "download.svg",
                                #     "extra_attributes": {
                                #         "@click": f"(() => {{ const baseUrl='{reverse('export_summary_report_excel')}'; const container=$event.currentTarget.closest('[x-id]'); const form=container?.querySelector('form'); if(!form) {{ window.location=baseUrl + window.location.search; return; }} const fd=new FormData(form); const params=new URLSearchParams(); for(const [k,v] of fd.entries()) params.append(k,v); const qs=params.toString(); window.location=baseUrl + (qs ? '?' + qs : ''); }})()",
                                #     },
                                # },
                            ]
                        ],
                        "position": "left",
                    },
                },
            ),
            TableAction(
                label='Thêm',
                icon='plus.svg',
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.FILLED,
                disabled=False,
                extra_attributes={
                    'menu': {
                        'groups': [
                             [
                                {
                                    'label': 'Thêm đơn lẻ',
                                    'icon': 'plus.svg',
                                    'extra_attributes': { 
                                        '@click': f'''$dispatch("modal:open", {{
                                            url: "{reverse("quota_create")}",
                                            title: "Thêm mới chỉ tiêu",
                                            ariaLabel: "Thêm mới chỉ tiêu",
                                            closeEvent: "quota:success",
                                        }});'''
                                    }
                                },
                                {
                                    'label': 'Thêm hàng loạt',
                                    'icon': 'file.svg',
                                    'extra_attributes': { 
                                        '@click': f'''$dispatch("modal:open", {{
                                        url: "{reverse("quota_import")}",
                                        title: "Thêm mới chỉ tiêu hàng loạt",
                                        ariaLabel: "Thêm mới chỉ tiêu hàng loạt",
                                        closeEvent: "quota:success",
                                    }});'''
                                    }
                                }
                            ],
                        ],
                        'position': 'right',
                    }
                }
            ),
        ]
    return actions

def row_actions(request):
    actions = [
        TableRowAction(
            icon='eye.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.OUTLINED,
            disabled=False,
            extra_attributes={
                '@click': f'''$dispatch("modal:open", {{
                    url: "{reverse("quota_detail", query={"id": "__ROW_ID__"})}",
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
                    url: "{reverse("quota_summary", query={"id": "__ROW_ID__"})}",
                    title: "Xem báo cáo chỉ tiêu",
                    ariaLabel: "Xem báo cáo chỉ tiêu"
                }});'''
            }
        ),
    ]
    if request.user.is_superuser:
        actions.extend([
            TableRowAction(
                icon='edit.svg',
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.OUTLINED,
                disabled=False,
                extra_attributes={
                    '@click': f'''$dispatch("modal:open", {{
                        url: "{reverse("quota_update", query={"id": "__ROW_ID__"})}",
                        title: "Cập nhật chỉ tiêu",
                        ariaLabel: "Cập nhật chỉ tiêu",
                        closeEvent: "quota:success",
                    }});'''
                }
            ),
            TableRowAction(
                icon='trash.svg',
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.FILLED,
                disabled=False,
                render_predicate=lambda row: not row['cannot_delete'],
                htmx_event_prefix='quota',
                extra_attributes={
                    'hx-get': f'{reverse("quota_delete", query={"id": "__ROW_ID__"})}',
                    'hx-swap': 'none',
                    'hx-confirm': 'Bạn có chắc chắn muốn xóa chỉ tiêu này không? Dữ liệu sẽ không thể khôi phục lại sau khi xóa.',
                }
            )
        ])
    return actions

def get_common_context(request):
    queryset = Quota.objects
    # Filter quotas for non-superusers
    department_id = request.user.profile.department_id
    if not request.user.is_superuser:
        queryset=queryset.filter(
            Exists(QuotaReport.objects.filter(quota=OuterRef('pk'), department_id=department_id)) | 
            Exists(QuotaAssignment.objects.filter(quota=OuterRef('pk'), department_id=department_id))
        )

    dept_queryset = QuotaAssignment.objects.filter(
        quota=OuterRef('pk'),
    )
    lead_dept_query = dept_queryset.filter(
        is_leader=True
    )
    DELIMITER = ', '
    # Lead department & assigned departments
    queryset = queryset.annotate(
        lead_department_id=Subquery(lead_dept_query.values('department_id')[:1]),
        lead_department_name=Subquery(lead_dept_query.values('department__short_name')[:1]),
        assigned_departments=Subquery(
            (
                dept_queryset.filter(is_leader=False)
                .values('quota_id')
                .annotate(assigned_departments=StringAgg('department__short_name', delimiter=DELIMITER, distinct=True))
                .values('assigned_departments')[:1]
            )
        ),
        cannot_delete=Exists(QuotaReport.objects.filter(quota=OuterRef('pk')).exclude(status=QuotaReport.Status.NOT_SENT))
    )

    COUNT_PREFIX = 'count-'
    # Status counts
    status_counts = {
        f"{COUNT_PREFIX}{val}": Count(
            'id', 
            filter=Q(status=val)
        )
        for val, _ in QuotaReport.Status.choices
    }
    period_ids = request.GET.getlist('period_ids', [])
    agg_filter = Q()
    if period_ids:
        agg_filter &= Q(period_id__in=period_ids)
    report_queryset = (
        QuotaReport.objects
        .filter(Q(quota_id=OuterRef('pk')) & agg_filter)
        .values('quota_id')
        .annotate(
            data=JSONObject(
                total_expected=Sum('expected_value'),
                total_actual=Sum('actual_value'),
                reported_departments=StringAgg('department__short_name', delimiter=DELIMITER, distinct=True),
                **status_counts
            )
        )
        .values('data')
    )

    privilege_filter = Q(Value(True))
    if not request.user.is_superuser:
        privilege_filter = Q(lead_department_id=request.user.profile.department_id)

    
    queryset = queryset.alias(
        report_data=Case(
            When(privilege_filter, then=Subquery(report_queryset[:1])),
            default=Subquery(report_queryset.filter(department_id=request.user.profile.department_id)[:1]),
        )
    ).alias(
        # Extract values from the JSON 'report_data'
        # Use Cast to ensure they are treated as floats for division
        total_actual=Cast(F('report_data__total_actual'), FloatField()),
        total_expected=Cast(F('report_data__total_expected'), FloatField()),
    ).annotate(
        report_data=F('report_data'),
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
        'assigned_departments',
        'report_data',
        'evaluation_result',
        'cannot_delete',
    ]

    queryset = queryset.values(*query_fields)

    def transformer(row):
        row['total_expected'] = row['report_data']['total_expected'] if row['report_data'] else None
        row['total_actual'] = row['report_data']['total_actual'] if row['report_data'] else None
        row['reported_departments'] = row['report_data']['reported_departments'] if row['report_data'] else ''
        row['completion_percent'] = row['total_actual'] / row['total_expected'] if row['total_expected'] else 0
        row['report_statuses'] = {}
        for status in QuotaReport.Status:
            row['report_statuses'][status] = row['report_data'][f"{COUNT_PREFIX}{status}"] if row['report_data'] else 0
        # Full assigned departments
        row['assigned_departments_full'] = row['assigned_departments']
        
        all_deps = f"{row['assigned_departments']}{DELIMITER}{row['reported_departments']}"
        deps = list({d for d in all_deps.split(DELIMITER) if d}) # Using a set comprehension
        count = len(deps)
        row['assigned_departments'] = f"{DELIMITER.join(deps[:2])}" + (f"{DELIMITER}+{count - 2}" if count >= 3 else "")
        return row

    table_context = TableContext(
        request=request,
        reload_event='quota:success',
        columns=COLUMNS,
        filters=table_filters(request),
        partial_url=reverse('quota_list_partial'),
        actions=table_actions(request),
        row_actions=row_actions(request),
        show_ordinal=True,
    )

    return {
        **table_context.to_response_context(queryset, transformer=transformer)
    }

@method_decorator(permission_required('app.view_quota'), name='dispatch')
class QuotaListView(ListView):
    model = Quota
    template_name = "quota/list.html"

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

class QuotaListPartialView(QuotaListView):
    template_name = "quota/partial.html"
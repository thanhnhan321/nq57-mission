from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import method_decorator
from django.db.models import (
    BigIntegerField,
    F,
    Q,
    Count,
    Exists,
    OuterRef,
    Subquery,
    Sum,
    TextField,
)
from django.db.models.functions import Coalesce
from django.contrib.postgres.aggregates import StringAgg
# from django.db import connection
from django.urls import reverse
from django.views.generic import ListView

from ...constants import OPTION_COLOR_CLASS_MAP
from ...models import Period, Quota, QuotaReport
from ..templates.components.button import Button
from ..templates.components.table import TableContext, TableAction, TableRowAction, FilterParam, TableColumn, MISSING
from ...utils.format import format_number
from ...handlers.period import get_quota_report_deadline

COUNT_PREFIX = 'count-'

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
        name='department__short_name',
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
    period_ids = kwargs.get('period_ids', [])
    if not period_ids:
        period_ids = MISSING
    def evaluation_result_query(value):
        if value:
            return Q(total_actual__gte=F('target_percent') * F('total_expected'))
        return Q(total_actual__isnull=True) | Q(total_actual__lt=F('target_percent') * F('total_expected'))
    
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
            query=lambda value: Exists(Q(department_reports__period_id__in=value)),
            extra_attributes={
                'options_url': reverse('period_options'),
            },
        ),
        FilterParam(
            name='lead_department_id',
            label='Đơn vị chủ trì',
            type=FilterParam.Type.SELECT,
            inner_type=FilterParam.Type.NUMBER,
            query=lambda value: Q(department_id=value),
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
                Q(department_reports__department_id=value) | 
                Q(department_assignments__department_id=value)
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
            query=lambda value: evaluation_result_query(value),
            placeholder='Tất cả',
            extra_attributes={
                'options_url': reverse('quota_evaluation_result_options'),
            },
        ),
    ]
    def status_query(value):
        filter = Q()
        for val in value:
            filter |= Q(**{f'{COUNT_PREFIX}{val}__gte': 1})
        return filter
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
    actions = [
        TableAction(
                label="Xuất báo cáo",
                icon="download.svg",
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.OUTLINED,
                disabled=False,
                loading_text="Đang xuất...",
                klass="!border-[#940001] !bg-white !text-red-700 hover:!border-red-700 hover:!bg-red-50 hover:!text-red-900 active:!bg-red-100",
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
    ]
    if request.user.is_superuser:
        actions.extend([
            TableAction(
                label='Thêm mới',
                icon='plus.svg',
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.FILLED,
                disabled=False,
                extra_attributes={
                    'menu': {
                        'groups': [
                            [
                                {
                                    'label': 'Thêm mới',
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
                                    'label': 'Thêm mới Excel',
                                    'icon': 'file.svg',
                                    'extra_attributes': { 
                                        '@click': f'''$dispatch("modal:open", {{
                                        url: "{reverse("quota_import")}",
                                        title: "Thêm mới từ Excel",
                                        ariaLabel: "Thêm mới từ Excel",
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
            TableAction(
                label='Mở/Khóa báo cáo',
                icon='lock.svg',
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.OUTLINED,
                disabled=False,
                extra_attributes={
                    '@click': f'''$dispatch("modal:open", {{
                        url: "{reverse("quota_period_toggle_confirm")}",
                        title: "Mở/Khóa kỳ báo cáo",
                        ariaLabel: "Mở/Khóa kỳ báo cáo"
                    }});'''
                }
            ),
        ])
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
                }});''',
                'title': 'Xem chi tiết',
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
                }});''',
                'title': 'Xem báo cáo chỉ tiêu',
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
                    }});''',
                    'title': 'Chỉnh sửa',
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
                    '@click': f'''$dispatch("modal:open", {{
                        url: "{reverse("quota_delete_confirm", query={"id": "__ROW_ID__"})}",
                        title: "Xóa chỉ tiêu",
                        ariaLabel: "Xóa chỉ tiêu"
                    }});''',
                    'title': 'Xóa',
                }
            )
        ])
    return actions

def get_common_context(request):
    queryset = (
        Quota.objects
        .select_related('department')
        .prefetch_related('department_assignments')
    )
    department_id = request.user.profile.department_id
    is_superuser = request.user.is_superuser
    if not is_superuser:
        queryset = queryset.filter(
            Q(department_id=department_id) | 
            Q(department_reports__department_id=department_id) | 
            Q(department_assignments__department_id=department_id)
        )

    DELIMITER = ', '
    queryset = queryset.annotate(
        assigned_departments=StringAgg(
            'department_assignments__department__short_name', 
            delimiter=DELIMITER,
            distinct=True,
        )
    )

    raw_period_ids = request.GET.getlist('period_ids', [])
    if raw_period_ids:
        period_ids = [int(x) for x in raw_period_ids]
    else:
        year = request.GET.get('year', '')

        period_ids = list(Period.objects.filter(year=year).values_list('id', flat=True)) if year else []
    # scoped_reports() is built on QuotaReport; OuterRef('pk') there is the report id, not quota id.
    user_is_quota_lead_for_report = Exists(
        Quota.objects.filter(
            id=OuterRef('quota_id'),
            department_id=department_id,
        )
    )

    def scoped_reports(quota_id_outer_ref=None):
        # Outer query is usually Quota → OuterRef('pk'). When nested under another
        # QuotaReport subquery (e.g. max_period_sq inside cum_*), pass OuterRef('quota_id').
        ref = OuterRef('pk') if quota_id_outer_ref is None else quota_id_outer_ref
        qs = QuotaReport.objects.filter(quota_id=ref)
        if period_ids:
            qs = qs.filter(period_id__in=period_ids)
        if not is_superuser:
            qs = qs.filter(Q(department_id=department_id) | user_is_quota_lead_for_report)
        return qs

    # Totals are computed as sum of deltas vs previous_report for *all* quota types:
    #   total = Σ (value - previous_report.value)
    # This makes cumulative and discrete quotas consistent when previous_report is populated.
    def delta_total_subquery(value_field: str, prev_value_field: str) -> Subquery:
        delta_expr = F(value_field)- Coalesce(F(prev_value_field), 0)
        return Subquery(
            scoped_reports()
            .exclude(status=QuotaReport.Status.NOT_SENT)
            .values('quota_id')
            .annotate(_s=Sum(delta_expr))
            .values('_s')[:1],
            output_field=BigIntegerField(),
        )

    total_expected_sq = delta_total_subquery('expected_value', 'previous_report__expected_value')
    total_actual_sq = delta_total_subquery('actual_value', 'previous_report__actual_value')

    reported = Subquery(
        scoped_reports()
        .values('quota_id')
        .annotate(_n=StringAgg('department__short_name', delimiter=DELIMITER, distinct=True))
        .values('_n')[:1],
        output_field=TextField(),
    )

    report_status_annotations = {}
    for val, _ in QuotaReport.Status.choices:
        status_filter = Q(department_reports__status=val)
        if period_ids:
            status_filter &= Q(department_reports__period_id__in=period_ids)
        status_filter &= Q() if is_superuser else (
            Q(department_reports__department_id=department_id) | Q(department_id=department_id)
        )
        report_status_annotations[f'{COUNT_PREFIX}{val}'] = Count('department_reports', filter=status_filter, distinct=True)

    queryset = queryset.alias(
        temp_expected=total_expected_sq,
        temp_actual=total_actual_sq,
    ).annotate(
        total_expected=F('temp_expected'),
        total_actual=F('temp_actual'),
        reported_departments=reported,
        **report_status_annotations,
    )

    query_fields = [
        'id',
        'name',
        'target_percent',
        'department_id',
        'department__short_name',
        'assigned_departments',
        'total_expected',
        'total_actual',
        'reported_departments',
    ]
    query_fields.extend(report_status_annotations.keys())

    queryset = queryset.values(*query_fields)

    def transformer(row):
        row['completion_percent'] = row['total_actual'] / row['total_expected'] if row['total_expected'] and row['total_actual'] else 0
        row['evaluation_result'] = True if row['total_expected'] and row['completion_percent'] >= row['target_percent'] else False
        row['report_statuses'] = {}
        row['cannot_delete'] = False
        for status in QuotaReport.Status:
            row['report_statuses'][status] = row[f'{COUNT_PREFIX}{status}']
            if status != QuotaReport.Status.NOT_SENT and row[f'{COUNT_PREFIX}{status}'] > 0:
                row['cannot_delete'] = True
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
        filters=table_filters(request, period_ids=period_ids),
        partial_url=reverse('quota_list_partial'),
        actions=table_actions(request),
        row_actions=row_actions(request),
        show_ordinal=True,
    )
    ctx = table_context.to_response_context(queryset, transformer=transformer)
    # print(connection.queries[-1]['sql'])
    return ctx

@method_decorator(permission_required('app.view_quota'), name='dispatch')
class QuotaListPartialView(ListView):
    model = Quota
    template_name = "quota/partial.html"

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

@method_decorator(permission_required('app.view_quota'), name='dispatch')
class QuotaListView(QuotaListPartialView):
    template_name = "quota/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = f'<a href="{reverse("quota_list")}" class="hover:underline">Chỉ tiêu</a>'
        deadline_alert = get_quota_report_deadline()
        context['deadline_alert'] = deadline_alert
        return context

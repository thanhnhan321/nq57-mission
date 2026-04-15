from collections import OrderedDict

from django.urls import reverse
from django.views.generic import ListView
from django.utils.html import format_html, format_html_join
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import method_decorator

from ....models.report import ReportPeriodMonth
from ...templates.components.button import Button
from ...templates.components.table import TableContext, TableRowAction, TableColumn


REPORT_TYPE_LABELS = {
    ReportPeriodMonth.ReportType.MONTH: "Báo cáo tháng",
    ReportPeriodMonth.ReportType.QUARTER: "Báo cáo quý",
    ReportPeriodMonth.ReportType.HALF_YEAR: "Báo cáo 6 tháng",
    ReportPeriodMonth.ReportType.NINE_MONTH: "Báo cáo 9 tháng",
    ReportPeriodMonth.ReportType.YEAR: "Báo cáo năm",
}


COLUMNS = [
    TableColumn(
        name="stt",
        label="STT",
        sortable=False,
    ),
    TableColumn(
        name="month_display",
        label="Tháng",
        sortable=False,
    ),
    TableColumn(
        name="report_types_display",
        label="Các loại báo cáo cần nộp",
        sortable=False,
    ),
]


FILTERS = []


def table_actions():
    return []


def row_actions():
    return [
        TableRowAction(
            icon="edit.svg",
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.OUTLINED,
            disabled=False,
            htmx_event_prefix="report-period-month",
            key="month",
            extra_attributes={
                "@click": f'''$dispatch("modal:open", {{
                    url: "{reverse("report_period_month_update", query={"month": "__ROW_ID__"})}",
                    title: "Cập nhật loại báo cáo theo tháng",
                    ariaLabel: "Cập nhật loại báo cáo theo tháng",
                    closeEvent: "report-period-month:success",
                }});''',
                'title': 'Chỉnh sửa',
            }
        ),
    ]


def _render_report_type_badges(labels):
    return format_html(
        '<div class="flex flex-wrap items-center justify-center gap-3 w-full">{}</div>',
        format_html_join(
            '',
            '<span class="inline-flex min-h-10 items-center rounded-lg border border-slate-200 bg-slate-100 px-4 text-sm font-medium text-slate-500 shadow-sm">{}</span>',
            ((label,) for label in labels),
        )
    )

def _build_base_rows():
    queryset = (
        ReportPeriodMonth.objects
        .all()
        .order_by("month", "report_type")
        .values("month", "report_type")
    )

    grouped = OrderedDict()
    for item in queryset:
        month = item["month"]
        grouped.setdefault(month, [])
        grouped[month].append(item["report_type"])

    rows = []
    for index, (month, report_types) in enumerate(grouped.items(), start=1):
        labels = [
            REPORT_TYPE_LABELS.get(report_type, report_type)
            for report_type in report_types
        ]

        rows.append({
            "stt": index,
            "month": month,
            "month_display": f"Tháng {month}",
            "report_types_display": _render_report_type_badges(labels),
        })

    return rows


def get_common_context(request):
    base_query = _build_base_rows()

    table_context = TableContext(
        request=request,
        reload_event="report-period-month:success",
        columns=COLUMNS,
        filters=FILTERS,
        partial_url=reverse("report_period_month_list_partial"),
        actions=table_actions(),
        row_actions=row_actions(),
    )

    return table_context.to_response_context(base_query)

@method_decorator(permission_required('app.view_reportperiodmonth'), name='dispatch')
class ReportPeriodMonthListPartialView(ListView):
    model = ReportPeriodMonth
    template_name = "categories/report_type/partial.html"

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

@method_decorator(permission_required('app.view_reportperiodmonth'), name='dispatch')
class ReportPeriodMonthListView(ReportPeriodMonthListPartialView):
    template_name = "categories/report_type/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = f'Danh mục / <a href="{reverse("report_period_month_list")}" class="hover:underline">Loại báo cáo theo tháng</a>'
        return context


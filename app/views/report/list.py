from django.db.models import Q, Case, When, Value, CharField
from django.templatetags.static import static
from django.urls import reverse
from django.views.generic import ListView
from django.utils.html import format_html
from django.utils import timezone

from ...handlers.period import get_department_report_deadline
from ...models import DepartmentReport, Department, Period
from ..templates.components.button import Button
from ..templates.components.table import TableContext, TableAction, TableRowAction, FilterParam, TableColumn


COLUMNS = [
    TableColumn(name="period_display", label="Kỳ Báo Cáo", sortable=False),
    TableColumn(name="report_type_display", label="Loại Báo Cáo", sortable=True),
    TableColumn(name="department__name", label="Đơn Vị", sortable=True, need_tooltip=True),
    TableColumn(name="file_name_html", label="File Báo Cáo", sortable=False),
    TableColumn(name="sent_at_display", label="Ngày Gửi", sortable=True),
    TableColumn(name="status_html", label="Tình Trạng", sortable=False),
]


def build_deadline_alert():
    deadline = get_department_report_deadline()
    if not deadline:
        return {
            "show": False,
            "deadline_text": "",
            "remaining_text": "",
            "is_overdue": False,
        }

    local_deadline = timezone.localtime(deadline)
    now = timezone.localtime()

    deadline_text = local_deadline.strftime("%H:%M %d/%m/%Y")

    diff = local_deadline - now
    is_overdue = diff.total_seconds() <= 0

    if is_overdue:
        remaining_text = ""
    else:
        total_seconds = int(diff.total_seconds())
        days = total_seconds // 86400
        remain = total_seconds % 86400
        hours = remain // 3600
        remain %= 3600
        minutes = remain // 60

        parts = []
        if days > 0:
            parts.append(f"{days} ngày")
        if hours > 0:
            parts.append(f"{hours} giờ")
        if minutes > 0:
            parts.append(f"{minutes} phút")

        remaining_text = " ".join(parts) if parts else "0 phút"

    return {
        "show": True,
        "deadline_text": deadline_text,
        "remaining_text": remaining_text,
        "is_overdue": is_overdue,
    }


def resolve_department_name_from_filter_value(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""

    dept = Department.objects.filter(id=value).values("name").first()
    if dept:
        return dept["name"]

    return value


def normalize_report_type(value: str) -> str:
    value = (value or "").strip()
    mapping = {
        "MONTH": "MONTH",
        "QUARTER": "QUARTER",
        "HALF_YEAR": "HALF_YEAR",
        "NINE_MONTH": "NINE_MONTH",
        "YEAR": "YEAR",
        "Báo cáo tháng": "MONTH",
        "Báo cáo quý": "QUARTER",
        "Báo cáo 6 tháng": "HALF_YEAR",
        "Báo cáo 9 tháng": "NINE_MONTH",
        "Báo cáo năm": "YEAR",
    }
    return mapping.get(value, value)


def normalize_status(value: str) -> str:
    value = (value or "").strip()
    mapping = {
        "SENT": "SENT",
        "NO_REPORT": "NO_REPORT",
        "Đã gửi": "SENT",
        "Không gửi": "NO_REPORT",
        "Chưa gửi": "NO_REPORT",
    }
    return mapping.get(value, value)


def parse_multiselect_values(values):
    result = []
    for value in values:
        if value in ("", "all", None):
            continue

        parts = [item.strip() for item in str(value).split(",") if item.strip()]
        result.extend(parts)

    unique_values = []
    seen = set()
    for item in result:
        if item not in seen:
            seen.add(item)
            unique_values.append(item)

    return unique_values


def resolve_period_ids_from_values(values):
    cleaned_values = [str(v).strip() for v in values if str(v).strip()]
    if not cleaned_values:
        return []

    numeric_ids = [int(v) for v in cleaned_values if v.isdigit()]
    label_values = [v for v in cleaned_values if not v.isdigit()]

    resolved_ids = list(numeric_ids)

    if label_values:
        period_qs = Period.objects.filter(
            Q(name__in=label_values) | Q(code__in=label_values)
        ).values_list("id", flat=True)
        resolved_ids.extend(period_qs)

    unique_ids = []
    seen = set()
    for item in resolved_ids:
        if item not in seen:
            seen.add(item)
            unique_ids.append(item)

    return unique_ids


def _is_report_admin(user) -> bool:
    return bool(getattr(user, "is_superuser", False))


def _get_user_department_id(user):
    profile = getattr(user, "profile", None)
    department_id = getattr(profile, "department_id", None)
    if department_id:
        return department_id
    return None


def table_filters(request):
    filters = [
        FilterParam(
            name="period_ids",
            label="Kỳ báo cáo",
            placeholder="Tất cả",
            type=FilterParam.Type.MULTISELECT,
            query=lambda value: Q(period_id__in=resolve_period_ids_from_values(value)),
            extra_attributes={
                "options_url": reverse("period_options"),
            },
        ),
        FilterParam(
            name="report_type",
            label="Loại báo cáo",
            placeholder="Tất cả",
            type=FilterParam.Type.SELECT,
            extra_attributes={
                "options_url": reverse("department_report_type_options"),
            },
            query=lambda value: Q(report_type=normalize_report_type(value)),
        ),
        FilterParam(
            name="status",
            label="Tình trạng",
            placeholder="Tất cả",
            type=FilterParam.Type.SELECT,
            extra_attributes={
                "options_url": reverse("department_report_status_options"),
            },
            query=lambda value: Q(status=normalize_status(value)),
        ),
    ]

    if _is_report_admin(request.user):
        filters.insert(
            1,
            FilterParam(
                name="department",
                label="Đơn vị",
                placeholder="Tất cả",
                type=FilterParam.Type.SELECT,
                extra_attributes={
                    "options_url": reverse("department_report_department_options"),
                },
                query=lambda value: (
                    Q(department_id=value) |
                    Q(department__name__iexact=resolve_department_name_from_filter_value(value))
                ),
            ),
        )

    return filters


def _get_first_period_value_from_request(request) -> str:
    raw_values = request.GET.getlist("period_ids")
    values = parse_multiselect_values(raw_values)

    if values:
        return str(values[0])

    raw_single = (request.GET.get("period_ids") or "").strip()
    if raw_single:
        return raw_single.split(",")[0].strip()

    return ""


def _get_department_value_from_request(request) -> str:
    return (request.GET.get("department") or "").strip()


def table_actions(request):
    selected_period = _get_first_period_value_from_request(request)

    is_admin = _is_report_admin(request.user)
    user_department_id = _get_user_department_id(request.user)

    if is_admin:
        selected_department_id = _get_department_value_from_request(request)
    else:
        selected_department_id = str(user_department_id or "")

    create_modal_url = reverse("department_report_create_modal")
    export_detail_url = reverse("export_detail_report_excel")
    export_summary_url = reverse("export_summary_report_excel")

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
                                "label": "Xuất báo cáo chi tiết",
                                "icon": "download.svg",
                                "extra_attributes": {
                                    "@click": f"""
                                        (() => {{
                                            const baseUrl = "{export_detail_url}";
                                            const form = $event.currentTarget.closest('[x-id]')?.querySelector('form');
                                            const params = form
                                                ? new URLSearchParams(new FormData(form))
                                                : new URLSearchParams(window.location.search);
                                            {"params.set('department', '" + str(user_department_id or "") + "');" if not is_admin else ""}
                                            window.location.href = baseUrl + (params.toString() ? '?' + params.toString() : '');
                                        }})()
                                    """,
                                },
                            },
                            {
                                "label": "Xuất báo cáo tổng hợp",
                                "icon": "download.svg",
                                "extra_attributes": {
                                    "@click": f"""
                                        (() => {{
                                            const baseUrl = "{export_summary_url}";
                                            const form = $event.currentTarget.closest('[x-id]')?.querySelector('form');
                                            const params = form
                                                ? new URLSearchParams(new FormData(form))
                                                : new URLSearchParams(window.location.search);
                                            {"params.set('department', '" + str(user_department_id or "") + "');" if not is_admin else ""}
                                            window.location.href = baseUrl + (params.toString() ? '?' + params.toString() : '');
                                        }})()
                                    """,
                                },
                            },
                        ]
                    ],
                    "position": "right",
                },
            },
        ),
    ]

    open_modal_js = (
        "(() => {"
        f"const url = new URL('{create_modal_url}', window.location.origin);"
        + (f"url.searchParams.set('period', '{selected_period}');" if selected_period else "")
        + (f"url.searchParams.set('department_id', '{selected_department_id}');" if selected_department_id else "")
        + "window.dispatchEvent(new CustomEvent('modal:open', { detail: { "
        + "url: url.pathname + url.search, "
        + "title: 'Thêm mới báo cáo', "
        + "ariaLabel: 'Thêm mới báo cáo', "
        + "closeEvent: 'department-report:reload' "
        + "} }));"
        + "})()"
    )

    actions.append(
        TableAction(
            label="Thêm mới",
            icon="plus.svg",
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.FILLED,
            disabled=False,
            loading_text="Đang mở...",
            extra_attributes={
                "@click": open_modal_js,
            },
        ),
    )

    return actions


def row_actions(request):
    actions = [
        TableRowAction(
            icon="download.svg",
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.FILLED,
            disabled=False,
            htmx_event_prefix="department-report",
            key="id",
            extra_attributes={
                "hx-get": reverse("department_report_download") + "?id=__ROW_ID__",
                "hx-swap": "none",
            },
        ),
        TableRowAction(
            icon="edit.svg",
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.OUTLINED,
            disabled=False,
            htmx_event_prefix="department-report",
            key="id",
            extra_attributes={
                "@click": f"""
                    (() => {{
                        const url = "{reverse('department_report_update', kwargs={'pk': 999999})}".replace("999999", "__ROW_ID__");
                        window.dispatchEvent(new CustomEvent("modal:open", {{
                            detail: {{
                                url: url,
                                title: "Cập nhật báo cáo",
                                ariaLabel: "Cập nhật báo cáo",
                                closeEvent: "department-report:reload"
                            }}
                        }}));
                    }})()
                """,
            },
        ),
    ]

    return actions


def build_file_html(file_name: str):
    file_name = file_name or ""
    if not file_name:
        return format_html('<span class="text-slate-400">--</span>')

    pdf_icon_url = static("icons/pdf.svg")
    return format_html(
        """
        <div class="flex items-center gap-2 min-w-0">
            <img src="{}" alt="PDF" class="h-4 w-4 shrink-0" />
            <span class="truncate font-semibold text-[#dc2626]">{}</span>
        </div>
        """,
        pdf_icon_url,
        file_name,
    )


def build_status_html(status: str):
    mapping = {
        "SENT": ("Đã gửi", "bg-[#2878f0] text-white"),
        "NO_REPORT": ("Không gửi", "bg-[#e5e5e5] text-[#c62828]"),
    }

    label, classes = mapping.get(
        status,
        ("Không gửi", "bg-[#e5e5e5] text-[#c62828]")
    )

    return format_html(
        """
        <div class="flex justify-center">
            <span class="inline-flex min-w-[116px] items-center justify-center rounded-full px-4 py-1 text-sm font-medium leading-5 {}">
                {}
            </span>
        </div>
        """,
        classes,
        label,
    )


def build_period_display(month, report_year):
    if month:
        return f"{int(month):02d}/{report_year}"
    return str(report_year)


def build_report_type_display(report_type):
    return dict(DepartmentReport.ReportType.choices).get(report_type, "")


def get_base_queryset():
    return (
        DepartmentReport.objects
        .select_related("department", "file", "period")
        .annotate(
            report_type_display=Case(
                *[
                    When(report_type=choice_value, then=Value(choice_label))
                    for choice_value, choice_label in DepartmentReport.ReportType.choices
                ],
                default=Value(""),
                output_field=CharField(),
            ),
        )
        .order_by("-created_at")
    )


def apply_filters(queryset, request):
    is_admin = _is_report_admin(request.user)
    user_department_id = _get_user_department_id(request.user)

    if not is_admin and user_department_id:
        queryset = queryset.filter(department_id=user_department_id)

    for filter_item in table_filters(request):
        if filter_item.type == FilterParam.Type.MULTISELECT:
            raw_values = request.GET.getlist(filter_item.name)
            values = parse_multiselect_values(raw_values)
            if values:
                queryset = queryset.filter(filter_item.query(values))
        else:
            value = (request.GET.get(filter_item.name) or "").strip()
            if value not in ("", "all"):
                queryset = queryset.filter(filter_item.query(value))

    return queryset


def build_table_context(request, include_filters=True, include_actions=True):
    filtered_queryset = apply_filters(get_base_queryset(), request)

    sort = (request.GET.get("sort") or "").strip()
    sort_direction = (request.GET.get("sort_direction") or "").strip().lower()

    if not sort:
        sort = "created_at"
    if sort == "created_at" and sort_direction not in ("asc", "desc"):
        sort_direction = "desc"

    base_query = filtered_queryset.values(
        "id",
        "department__name",
        "month",
        "report_year",
        "report_type",
        "file_name",
        "sent_at",
        "status",
        "created_at",
    )

    table_context = TableContext(
        request=request,
        reload_event="department-report:reload",
        columns=COLUMNS,
        filters=table_filters(request) if include_filters else [],
        partial_url=reverse("department_report_list_partial"),
        actions=table_actions(request=request) if include_actions else [],
        row_actions=row_actions(request=request),
        show_ordinal=True,
    )

    context = table_context.to_response_context(base_query)

    context["sort"] = sort
    context["sort_direction"] = sort_direction

    rows = context.get("rows", [])
    for row in rows:
        row["period_display"] = build_period_display(row.get("month"), row.get("report_year"))
        row["report_type_display"] = build_report_type_display(row.get("report_type"))
        row["file_name_html"] = build_file_html(row.get("file_name"))

        sent_at = row.get("sent_at")
        row["sent_at_display"] = timezone.localtime(sent_at).strftime("%d/%m/%Y") if sent_at else ""
        row["status_html"] = build_status_html(row.get("status"))

    context["rows"] = rows
    context["deadline_alert"] = build_deadline_alert()
    return context


class DepartmentReportListView(ListView):
    model = DepartmentReport
    template_name = "report/list.html"

    def get_context_data(self, **kwargs):
        return build_table_context(self.request, include_filters=True, include_actions=True)


class DepartmentReportListPartialView(ListView):
    model = DepartmentReport
    template_name = "report/partial.html"

    def get_context_data(self, **kwargs):
        return build_table_context(self.request)
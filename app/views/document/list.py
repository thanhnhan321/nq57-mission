from datetime import date

from django.db.models import Q, Case, When, Value, CharField
from django.templatetags.static import static
from django.urls import reverse
from django.views.generic import ListView
from django.utils.html import format_html
from django.contrib.auth.decorators import permission_required
from django.utils.decorators import method_decorator

from ...models import Document, Department
from ..templates.components.button import Button
from ..templates.components.table import TableContext, TableAction, TableRowAction, FilterParam, TableColumn


COLUMNS = [
    TableColumn(name="type__name", label="Loại Văn Bản", sortable=True),
    TableColumn(name="code", label="Số Văn Bản", sortable=True),
    TableColumn(name="title", label="Tên Văn Bản", sortable=True, need_tooltip=True),
    TableColumn(name="issued_at", label="Ngày Ban Hành", sortable=True, type=TableColumn.Type.DATE),
    TableColumn(name="issued_by", label="Đơn Vị Ban Hành", sortable=True),
    TableColumn(name="status", label="Tình Trạng", sortable=False),
    TableColumn(name="expired_at_display", label="Ngày Hết Hiệu Lực", sortable=True),
    TableColumn(name="object__file_name", label="File Văn Bản", sortable=False),
]

def resolve_department_name_from_filter_value(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""

    dept = Department.objects.filter(id=value).values("name").first()
    if dept:
        return dept["name"]

    return value
def table_filters():
    return [
        FilterParam(
            name='period_ids',
            label='Kỳ báo cáo',
            placeholder='Tất cả',
            type=FilterParam.Type.MULTISELECT,
            query=lambda value: Q(period_id__in=value),
            extra_attributes={
                'options_url': reverse('period_options'),
            },
        ),
        FilterParam(
            name="code",
            label="Số văn bản",
            placeholder="Tất cả",
            type=FilterParam.Type.SELECT,
            extra_attributes={"options_url": reverse("document_number_options")},
            query=lambda value: Q(code__icontains=value),
        ),
        FilterParam(
            name="title",
            label="Tên văn bản",
            placeholder="Tất cả",
            type=FilterParam.Type.SELECT,
            extra_attributes={"options_url": reverse("document_name_options")},
            query=lambda value: Q(title__icontains=value),
        ),
        FilterParam(
            name="issued_by",
            label="Đơn vị ban hành",
            placeholder="Tất cả",
            type=FilterParam.Type.SELECT,
            extra_attributes={"options_url": reverse("department_report_department_options")},
            query=lambda value: Q(issued_by__iexact=resolve_department_name_from_filter_value(value)),
        ),
        FilterParam(
            name="status",
            label="Tình trạng",
            type=FilterParam.Type.SELECT,
            placeholder="Tất cả",
            extra_attributes={"options_url": reverse("document_status_options")},
            query=lambda value: (
                (Q(expired_at__isnull=True) | Q(expired_at__gte=date.today())) if value == "active"
                else Q(expired_at__lt=date.today()) if value == "expired"
                else Q()
            ),
        ),
    ]


def table_actions(request):
    actions = []
    if request.user.is_superuser:
        actions.extend(
            [
                TableAction(
                    label="Xuất báo cáo",
                    icon="download.svg",
                    icon_position=Button.IconPosition.LEFT,
                    variant=Button.Variant.OUTLINED,
                    disabled=False,
                    extra_attributes={
                        "hx-get": reverse("document_export"),
                        "hx-swap": "none",
                    },
                ),
                TableAction(
                    label="Thêm mới",
                    icon="plus.svg",
                    icon_position=Button.IconPosition.LEFT,
                    variant=Button.Variant.FILLED,
                    disabled=False,
                    extra_attributes={
                        '@click': f'''$dispatch("modal:open", {{
                            url: "{reverse("document_create")}",
                            title: "Thêm mới văn bản",
                            ariaLabel: "Thêm mới văn bản",
                            closeEvent: "document:success",
                        }});'''
                    },
                )
            ]
        )
    return actions


def row_actions(request):
    actions = [
        TableRowAction(
            icon="download.svg",
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.FILLED,
            disabled=False,
            htmx_event_prefix="document",
            key="code",
            extra_attributes={
                "hx-get": f'{reverse("document_download", query={"code": "__ROW_ID__"})}',
                "hx-swap": "none",
                "title": "Tải xuống",
            },
        ),
    ]

    if request.user.is_superuser:
        actions.extend([
            TableRowAction(
                icon="edit.svg",
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.OUTLINED,
                disabled=False,
                htmx_event_prefix="document",
                key="code",
                extra_attributes={
                    '@click': f'''$dispatch("modal:open", {{
                        url: "{reverse("document_update", query={"code": "__ROW_ID__"})}",
                        title: "Cập nhật văn bản",
                        ariaLabel: "Cập nhật văn bản",
                        closeEvent: "document:success",
                    }});''',
                    "title": "Chỉnh sửa",
                },
            ),
            TableRowAction(
                icon="trash.svg",
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.FILLED,
                disabled=False,
                htmx_event_prefix="document",
                key="code",
                extra_attributes={
                    '@click': f'''$dispatch("modal:open", {{
                        url: "{reverse("document_delete_confirm", query={"code": "__ROW_ID__"})}",
                        title: "Xác nhận xóa văn bản",
                        ariaLabel: "Xác nhận xóa văn bản",
                        closeEvent: "document:success",
                    }});''',
                    "title": "Xóa",
                },
            ),
        ])

    return actions


def build_file_html(file_name: str):
    file_name = file_name or ""
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
    classes = "bg-[#2878f0] text-white" if status == "Hiệu lực" else "bg-[#e5e5e5] text-[#c62828]"
    return format_html(
        """
        <div class="flex justify-center">
            <span class="inline-flex min-w-[116px] items-center justify-center rounded-full px-4 py-1 text-sm font-medium leading-5 {}">
                {}
            </span>
        </div>
        """,
        classes,
        status,
    )


def get_base_queryset():
    return (
        Document.objects
        .select_related("type", "object")
        .annotate(
            status=Case(
                When(expired_at__isnull=True, then=Value("Hiệu lực")),
                When(expired_at__gte=date.today(), then=Value("Hiệu lực")),
                default=Value("Hết hiệu lực"),
                output_field=CharField(),
            )
        )
    )


def apply_filters(queryset, request):
    for filter_item in table_filters():
        if filter_item.type == FilterParam.Type.MULTISELECT:
            value = request.GET.getlist(filter_item.name)
            value = [v for v in value if v not in ("", "all")]
            if value:
                queryset = queryset.filter(filter_item.query(value))
        else:
            value = request.GET.get(filter_item.name)
            if value not in (None, "", "all"):
                queryset = queryset.filter(filter_item.query(value))
    return queryset


def build_summary_cards(filtered_queryset):
    return [
        {"icon": "📄", "value": filtered_queryset.count(), "label": "TỔNG VĂN BẢN"},
        {"icon": "📝", "value": filtered_queryset.filter(type__code="NQ").count(), "label": "NGHỊ QUYẾT"},
        {"icon": "📊", "value": filtered_queryset.filter(type__code="CV").count(), "label": "CÔNG VĂN"},
        {"icon": "📋", "value": filtered_queryset.exclude(type__code__in=["NQ", "CV"]).count(), "label": "TỜ TRÌNH, ĐỀ XUẤT, KHÁC"},
    ]


def get_common_context(request):
    filtered_queryset = apply_filters(get_base_queryset(), request)

    base_query = filtered_queryset.values(
        "code",
        "title",
        "type__name",
        "issued_at",
        "issued_by",
        "expired_at",
        "object__file_name",
        "status",
    )

    table_context = TableContext(
        request=request,
        reload_event="document:success",
        columns=COLUMNS,
        filters=table_filters(),
        partial_url=reverse("document_list_partial"),
        actions=table_actions(request=request),
        row_actions=row_actions(request=request),
        show_ordinal=True,
    )

    context = table_context.to_response_context(base_query)

    rows = context.get("rows", [])
    for row in rows:
        row["object__file_name"] = build_file_html(row.get("object__file_name"))
        row["status"] = build_status_html(row.get("status"))
        expired_at = row.get("expired_at")
        row["expired_at_display"] = expired_at.strftime("%d/%m/%Y") if expired_at else ""

    context["rows"] = rows
    context["summary_cards"] = build_summary_cards(filtered_queryset)
    return context

@method_decorator(permission_required('app.view_document'), name='dispatch')
class DocumentListPartialView(ListView):
    model = Document
    template_name = "document/partial.html"

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

@method_decorator(permission_required('app.view_document'), name='dispatch')
class DocumentListView(DocumentListPartialView):
    template_name = "document/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = f'<a href="{reverse("document_list")}" class="hover:underline">Văn bản</a>'
        return context


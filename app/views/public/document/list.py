from django.db.models import Q, Case, When, Value, CharField
from django.templatetags.static import static
from django.urls import reverse
from django.utils.timezone import localdate
from django.views.generic import ListView
from django.utils.html import format_html

from ....constants import OPTION_COLOR_CLASS_MAP
from ....models import Document
from ...templates.components.table import TableContext, FilterParam, TableColumn


def build_status_badge(status: str):
    color = 'blue' if status == 'active' else 'red'
    classes = OPTION_COLOR_CLASS_MAP[color]
    label = "Hiệu lực" if status == "active" else "Hết hiệu lực"
    return format_html(
        """
        <span class="rounded-full {} text-xs px-2 py-1">{}</span>
        """,
        classes,
        label,
    )
def build_download_anchor(row):
    code = row["code"]
    file_name = row["object__file_name"]
    pdf_icon_url = static("icons/pdf.svg")
    return format_html(
        """
        <a class="w-fit flex items-center gap-2" href="{}" download="{}">
            <img src="{}" alt="PDF" class="h-4 w-4 shrink-0" />
            <span class="truncate font-semibold text-red-500">{}</span>
        </a>
        """,
        reverse("public_document_download", query={"code": code}),
        file_name,
        pdf_icon_url,
        file_name,
    )

COLUMNS = [
    TableColumn(
        name="type__name",
        label="Loại Văn Bản"
    ),
    TableColumn(
        name="code",
        label="Số Văn Bản",
        align=TableColumn.Align.LEFT,
    ),
    TableColumn(
        name="title",
        label="Tên Văn Bản",
        need_tooltip=True,
        align=TableColumn.Align.LEFT,
    ),
    TableColumn(
        name="issued_at",
        label="Ngày Ban Hành",
        sortable=True,
        type=TableColumn.Type.DATE,
    ),
    TableColumn(
        name="issued_by",
        label="Đơn Vị Ban Hành",
    ),
    TableColumn(
        name="object__file_name",
        label="File Văn Bản",
        is_hypertext=True,
        formatter=build_download_anchor,
    ),
    TableColumn(
        name="status",
        label="Tình Trạng",
        type=TableColumn.Type.BADGE,
        formatter=build_status_badge,
    ),
]


def table_filters():
    return [
        FilterParam(
            name="search",
            label="Kỳ báo cáo",
            placeholder="Tất cả",
            type=FilterParam.Type.MULTISELECT,
            inner_type=FilterParam.Type.NUMBER,
            extra_attributes={
                "options_url": reverse("period_options"),
            },
            query=lambda value: Q(period_id__in=value),
        ),
        FilterParam(
            name="code",
            label="Văn bản",
            placeholder="Tất cả",
            type=FilterParam.Type.TEXT,
            query=lambda value: Q(code__startswith=value) | Q(title__icontains=value),
        ),
        FilterParam(
            name="issued_by",
            label="Đơn vị ban hành",
            placeholder="Tất cả",
            type=FilterParam.Type.SELECT,
            extra_attributes={"options_url": reverse("department_report_department_options")},
            query=lambda value: Q(issued_by__icontains=value),
        ),
        FilterParam(
            name="status",
            label="Tình trạng",
            type=FilterParam.Type.SELECT,
            placeholder="Tất cả",
            extra_attributes={"options_url": reverse("document_status_options")},
            query=lambda value: Q(status=value),
        ),
        
    ]

def build_summary_cards(filtered_queryset):
    return [
        {"icon": "📄", "value": filtered_queryset.count(), "label": "TỔNG VĂN BẢN"},
        {"icon": "📝", "value": filtered_queryset.filter(type__code="NQ").count(), "label": "NGHỊ QUYẾT"},
        {"icon": "📊", "value": filtered_queryset.filter(type__code="CV").count(), "label": "CÔNG VĂN"},
        {"icon": "📋", "value": filtered_queryset.exclude(type__code__in=["NQ", "CV"]).count(), "label": "TỜ TRÌNH, ĐỀ XUẤT, KHÁC"},
    ]


def get_common_context(request):
    queryset = (
        Document.objects
        .select_related("type", "object")
        .annotate(
            status=Case(
                When(Q(expired_at__isnull=True) | Q(expired_at__gte=localdate()), then=Value("active")),
                default=Value("expired"),
                output_field=CharField(),
            )
        )
    )

    queryset = queryset.values(
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
        columns=COLUMNS,
        filters=table_filters(),
        partial_url=reverse("public_document_list_partial"),
        show_ordinal=True,
    )

    context = table_context.to_response_context(queryset)
    context["summary_cards"] = build_summary_cards(context["data_set"])
    
    return {
        **context,
    }


class PublicDocumentListView(ListView):
    model = Document
    template_name = "public/document/list.html"

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)


class PublicDocumentListPartialView(PublicDocumentListView):
    template_name = "public/document/partial.html"
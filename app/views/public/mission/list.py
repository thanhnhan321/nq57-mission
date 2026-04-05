from django.db.models import F, OuterRef, Q, Subquery
from django.shortcuts import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.generic import ListView

from app.models.mission import Mission, MissionReport
from app.utils.format import format_date
from ...templates.components.table import TableContext, FilterParam, TableColumn


def _render_badge(text: str | None, tone: str = "gray") -> str:
    if not text or text == "—":
        return ""

    tone_map = {
        "gray": "bg-slate-100 text-slate-500",
        "blue": "bg-blue-100 text-blue-600",
        "green": "bg-emerald-100 text-emerald-600",
        "yellow": "bg-amber-100 text-amber-600",
        "red": "bg-red-100 text-red-500",
        "orange": "bg-orange-100 text-orange-500",
    }
    klass = tone_map.get(tone, tone_map["gray"])

    return mark_safe(
        f'<span class="inline-flex items-center rounded-full px-3 py-1 text-xs font-medium whitespace-nowrap {klass}">{text}</span>'
    )


def _status_label_formatter(value):
    tone_map = {
        "Chưa thực hiện đúng hạn": "gray",
        "Chưa thực hiện trễ hạn": "red",
        "Đang thực hiện đúng hạn": "blue",
        "Đang thực hiện trễ hạn": "orange",
        "Hoàn thành đúng hạn": "green",
        "Hoàn thành trễ hạn": "yellow",
    }
    return _render_badge(value, tone_map.get(value, "gray"))


def _report_status_label_formatter(value):
    tone_map = {
        "Chưa gửi": "yellow",
        "Chờ phê duyệt": "blue",
        "Đã gửi": "green",
        "Không gửi": "red",
    }
    return _render_badge(value, tone_map.get(value, "gray"))


def _mission_name_column_formatter(row):
    if not row.get("name"):
        return ""

    mission_id = row.get("id") or row.get("code")

    return f'''
    <span
        class="text-blue-500 hover:underline cursor-pointer"
        @click="$dispatch('modal:open', {{
            url: '{reverse("public_mission_detail")}?id={mission_id}',
            title: 'Chi tiết nhiệm vụ',
            ariaLabel: 'Chi tiết nhiệm vụ'
        }});">
        {row['name']}
    </span>
    '''


def _mission_date_formatter(value):
    if value is None:
        return ""
    return format_date(value)


def _mission_report_content_formatter(value):
    if value is None:
        return ""
    return str(value).strip()


def _get_report_status_label(report_status_value: str | None) -> str:
    label_map = {
        "NOT_SENT": "Chưa gửi",
        "APPROVED": "Đã gửi",
        "SENT": "Đã gửi",
        "NO_REPORT": "Không gửi",
    }
    return label_map.get(report_status_value, "")


def _get_mission_status_label(mission_status_value: str | None) -> str:
    if not mission_status_value:
        return ""
    try:
        return MissionReport.MissionStatus(mission_status_value).label
    except ValueError:
        return ""


def _mission_status_column_formatter(value):
    label = _get_mission_status_label(value)
    if not label:
        return ""
    return _status_label_formatter(label)


def _report_status_column_formatter(value):
    label = _get_report_status_label(value)
    if not label:
        return ""
    return _report_status_label_formatter(label)


MISSION_COLUMNS = [
    TableColumn(
        name="van_ban",
        label="Văn bản",
        sortable=False,
        need_tooltip=True,
    ),
    TableColumn(
        name="name",
        label="Nhiệm vụ",
        formatter=_mission_name_column_formatter,
        sortable=True,
        need_tooltip=True,
        is_hypertext=True,
    ),
    TableColumn(
        name="report_content",
        label="Kết quả",
        sortable=False,
        need_tooltip=True,
        formatter=_mission_report_content_formatter,
    ),
    TableColumn(
        name="due_date",
        label="Thời hạn",
        sortable=True,
        type=TableColumn.Type.DATE,
        formatter=_mission_date_formatter,
    ),
    TableColumn(
        name="mission_status",
        label="Trạng thái",
        sortable=True,
        formatter=_mission_status_column_formatter,
        need_tooltip=False,
    ),
    TableColumn(
        name="department__short_name",
        label="Chủ trì",
        sortable=True,
        need_tooltip=False,
    ),
    TableColumn(
        name="report_status",
        label="Tình trạng báo cáo",
        sortable=True,
        formatter=_report_status_column_formatter,
        need_tooltip=False,
    ),
]


def _parse_int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    if str(value).strip() == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_multi_values(request, key: str) -> list[str]:
    values = request.GET.getlist(key)
    if values:
        return [str(v).strip() for v in values if str(v).strip() != ""]

    raw = request.GET.get(key)
    if not raw:
        return []

    if isinstance(raw, str) and "," in raw:
        return [part.strip() for part in raw.split(",") if part.strip()]

    return [str(raw).strip()] if str(raw).strip() else []


def get_public_mission_table_context(request):
    directive_level = request.GET.get("directive_level", "")
    directive_document = request.GET.get("directive_document", "")
    department_values = _parse_multi_values(request, "department")
    status_values = _parse_multi_values(request, "status")
    report_status_values = _parse_multi_values(request, "report_status")

    selected_year = _parse_int_or_none(request.GET.get("year")) or timezone.localdate().year

    # Report gần nhất trong năm -> dùng cho status
    latest_report_base = (
        MissionReport.objects
        .filter(
            mission_id=OuterRef("pk"),
            report_year=selected_year,
        )
        .order_by("-report_month", "-created_at", "-id")
    )

    # Report gần nhất trong năm mà CÓ nội dung -> dùng cho cột kết quả
    latest_report_with_content_base = (
        MissionReport.objects
        .filter(
            mission_id=OuterRef("pk"),
            report_year=selected_year,
            content__isnull=False,
        )
        .exclude(content__exact="")
        .order_by("-report_month", "-created_at", "-id")
    )

    queryset = (
        Mission.objects.filter(is_active=True)
        .annotate(
            report_status=Subquery(latest_report_base.values("status")[:1]),
            mission_status=Subquery(latest_report_base.values("mission_status")[:1]),
            report_content=Subquery(latest_report_with_content_base.values("content")[:1]),
            latest_report_month=Subquery(latest_report_base.values("report_month")[:1]),
            latest_report_year=Subquery(latest_report_base.values("report_year")[:1]),
            id=F("code"),
        )
        .select_related(
            "department",
            "directive_document",
            "directive_document__directive_level",
        )
        .distinct()
        .order_by("-created_at", "-code")
    )

    def directive_document_query(value: str):
        pk = (value or "").strip()
        return Q() if not pk else Q(directive_document_id=pk)

    def directive_level_query(value: str):
        level_id = _parse_int_or_none(value)
        return Q() if level_id is None else Q(directive_document__directive_level_id=level_id)

    def department_query(values: list[str]):
        if not values:
            return Q()
        ids = [_parse_int_or_none(v) for v in values]
        ids = [i for i in ids if i is not None]
        return Q() if not ids else Q(department_id__in=ids)

    def status_query(values: list[str]):
        return Q() if not values else Q(mission_status__in=values)

    def report_status_query(values: list[str]):
        return Q() if not values else Q(report_status__in=values)

    queryset = queryset.values(
        "id",
        "code",
        "name",
        "due_date",
        "mission_status",
        "report_status",
        "report_content",
        "department__short_name",
        "directive_document__code",
        "latest_report_month",
        "latest_report_year",
    )

    def transformer(row):
        row["id"] = row.get("code") or row.get("id") or ""
        row["van_ban"] = (row.get("directive_document__code") or "").strip()
        return row

    table_ctx = TableContext(
        request=request,
        columns=MISSION_COLUMNS,
        partial_url=reverse("public_mission_list_partial"),
        filters=[
            FilterParam(
                name="directive_level",
                label="Cấp chỉ đạo",
                placeholder="Tất cả",
                type=FilterParam.Type.SELECT,
                value=directive_level,
                extra_attributes={
                    "options_url": reverse("directive_level_options"),
                    "@change": (
                        "$dispatch('mission-filter:directive-level-changed', "
                        "{ directive_level: $event.target.value || '', reset: true });"
                    ),
                },
                query=directive_level_query,
            ),
            FilterParam(
                name="directive_document",
                label="Văn bản chỉ đạo",
                placeholder="Tất cả",
                type=FilterParam.Type.SELECT,
                value=directive_document,
                extra_attributes={
                    "options_url": reverse("mission_directive_document_all_options"),
                    "reload_events": ["mission-filter:directive-level-changed"],
                },
                query=directive_document_query,
            ),
            FilterParam(
                name="department",
                label="Đơn vị chủ trì",
                placeholder="Tất cả",
                type=FilterParam.Type.MULTISELECT,
                value=department_values,
                extra_attributes={
                    "options_url": reverse("department_options", query={"scope": "lead"}),
                },
                query=department_query,
            ),
            FilterParam(
                name="status",
                label="Trạng thái",
                placeholder="Tất cả",
                type=FilterParam.Type.MULTISELECT,
                value=status_values,
                extra_attributes={
                    "options_url": reverse("mission_status_options"),
                },
                query=status_query,
            ),
            FilterParam(
                name="report_status",
                label="Tình trạng báo cáo",
                placeholder="Tất cả",
                type=FilterParam.Type.MULTISELECT,
                value=report_status_values,
                extra_attributes={
                    "options_url": reverse("mission_report_status_options"),
                },
                query=report_status_query,
            ),
        ],
        actions=[],
        row_actions=[],
        bulk_actions=[],
        show_ordinal=True,
    )

    return {
        **table_ctx.to_response_context(queryset, transformer=transformer)
    }


class MissionReportListView(ListView):
    model = Mission
    template_name = "public/mission/list.html"

    def get_context_data(self, **kwargs):
        return get_public_mission_table_context(self.request)


class MissionReportListPartialView(ListView):
    model = Mission
    template_name = "public/mission/partial.html"

    def get_context_data(self, **kwargs):
        return get_public_mission_table_context(self.request)
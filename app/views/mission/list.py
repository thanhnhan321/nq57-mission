from types import SimpleNamespace

from django.db.models import F, OuterRef, Q, Subquery
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, render, reverse
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_GET
from django.views.generic import ListView
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import method_decorator

from ...models.department import UserProfile
from ...models.mission import Mission, MissionReport
from ...utils.format import format_date
from ..templates.components.button import Button
from ..templates.components.table import (
    FilterParam,
    TableAction,
    TableRowAction,
    TableColumn,
    TableContext,
)

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
        "Chưa gửi": "orange",
        "Chờ phê duyệt": "blue",
        "Đã gửi": "green",
        "Không gửi": "gray",
    }
    return _render_badge(value, tone_map.get(value, "gray"))


def _mission_name_column_formatter(row):
    if not row.get("name"):
        return ""

    mission_code = row.get("code")
    if not mission_code:
        return row.get("name", "")

    return f"""
    <span
        class="text-blue-500 hover:underline cursor-pointer"
        @click="$dispatch('modal:open', {{
            url: '{reverse("mission_detail_modal", kwargs={"pk": mission_code})}',
            title: 'Chi tiết nhiệm vụ',
            ariaLabel: 'Chi tiết nhiệm vụ'
        }});">
        {row["name"]}
    </span>
    """


def _mission_date_formatter(value):
    if value is None:
        return ""
    return format_date(value)


def _mission_report_content_formatter(value):
    if value is None:
        return ""
    return str(value).strip()


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
        # sortable=False,
        # need_tooltip=True,
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
        name="completed_date",
        label="Hoàn thành",
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
        # need_tooltip=False,
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


def _get_report_status_label(report_status_value: str | None) -> str:
    label_map = {
        "NOT_SENT": "Chưa gửi",
        "APPROVED": "Đã gửi",
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


def get_mission_table_context(request):
    is_mission_admin = getattr(request.user, "is_superuser", False)
    force_department_ids: list[int] = []

    report_period_raw = (request.GET.get("report_period") or "").strip()
    directive_document = request.GET.get("directive_document", "")
    department_values = _parse_multi_values(request, "department")
    status_values = _parse_multi_values(request, "status")
    report_status_values = _parse_multi_values(request, "report_status")

    if not is_mission_admin and not department_values:
        my_department_id = getattr(
            getattr(request.user, "profile", None),
            "department_id",
            None,
        )
        if my_department_id is None:
            my_department_id = (
                UserProfile.objects.filter(user_id=request.user.id)
                .values_list("department_id", flat=True)
                .first()
            )
        if my_department_id is not None:
            department_values = [str(my_department_id)]
            force_department_ids = [int(my_department_id)]

    # =========================
    # KỲ BÁO CÁO: default = TẤT CẢ
    # =========================
    selected_period_id = None
    report_period = ""

    if report_period_raw:
        selected_period_id = _parse_int_or_none(report_period_raw)
        if selected_period_id is not None:
            report_period = str(selected_period_id)

    # =========================
    # SUBQUERY REPORT
    # - Có chọn kỳ báo cáo: lấy report của đúng kỳ đó
    # - Không chọn (Tất cả): lấy report gần nhất
    # =========================
    report_base = MissionReport.objects.filter(mission_id=OuterRef("pk"))

    if selected_period_id is not None:
        report_base = report_base.filter(
            period_id=selected_period_id,
        ).order_by("-created_at", "-id")
    else:
        report_base = report_base.order_by(
            "-report_year", "-report_month", "-created_at", "-id"
        )

    queryset = (
        Mission.objects.filter(is_active=True)
        .annotate(
            report_status=Subquery(report_base.values("status")[:1]),
            mission_status=Subquery(report_base.values("mission_status")[:1]),
            report_content=Subquery(report_base.values("content")[:1]),
            id=F("code"),
        )
        .select_related(
            "department",
            "owner",
            "directive_document",
            "directive_document__directive_level",
        )
        .prefetch_related("assignee_departments")
        .distinct()
        .order_by(
            "start_date",
            F("completed_date").desc(nulls_last=True),
            "-code",
        )
    )

    if force_department_ids:
        queryset = queryset.filter(department_id__in=force_department_ids)

    def report_period_query(value: str):
        if not value or str(value).strip() == "":
            # TẤT CẢ => không filter theo kỳ báo cáo
            return Q()

        period_id = _parse_int_or_none(value)
        if period_id is None:
            return Q()

        return Q(reports__period_id=period_id)

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

    directive_document_options_url = reverse("mission_directive_document_all_options")

    _row_detail_modal_url_tpl = reverse(
        "mission_detail_modal",
        kwargs={"pk": "__ROW_ID__"},
    )
    _row_delete_confirm_modal_url_tpl = reverse(
        "mission_delete_table_modal",
        kwargs={"pk": "__ROW_ID__"},
    )

    detail_row_icon = "edit.svg" if is_mission_admin else "eye.svg"
    detail_row_action_label = "Chỉnh sửa" if is_mission_admin else "Xem chi tiết"

    queryset = queryset.values(
        "id",
        "code",
        "name",
        "due_date",
        "completed_date",
        "mission_status",
        "report_status",
        "report_content",
        "department__short_name",
        "directive_document__code",
    )

    def transformer(row):
        row["id"] = row.get("code") or row.get("id") or ""
        row["van_ban"] = (row.get("directive_document__code") or "").strip()
        return row

    table_ctx = TableContext(
        request=request,
        reload_event="mission:success",
        columns=MISSION_COLUMNS,
        partial_url=reverse("mission_list_partial"),
        filters=[
            FilterParam(
                name="report_period",
                label="Kỳ báo cáo",
                placeholder="Tất cả",
                type=FilterParam.Type.SELECT,
                value=report_period,   # default là ""
                extra_attributes={
                    "options_url": reverse("period_options"),
                },
                query=report_period_query,
            ),
            FilterParam(
                name="name",
                label="Nhiệm vụ",
                placeholder="Tất cả",
                type=FilterParam.Type.SELECT,
                value=request.GET.get("name", "").strip(),
                extra_attributes={
                    "options_url": reverse("mission_name_options"),
                },
                query=lambda v: Q(code=v.strip()) if v and str(v).strip() else Q(),
            ),
            FilterParam(
                name="directive_level",
                label="Cấp chỉ đạo",
                placeholder="Tất cả",
                type=FilterParam.Type.SELECT,
                inner_type=FilterParam.Type.NUMBER,
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
                    "options_url": directive_document_options_url,
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
        actions=[
            TableAction(
                label="Xuất báo cáo",
                icon="download.svg",
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.OUTLINED,
                disabled=False,
                loading_text="Đang xuất.",
                klass="!border-[#940001] !bg-white !text-red-700 hover:!border-red-700 hover:!bg-red-50 hover:!text-red-900 active:!bg-red-100",
                extra_attributes={
                    "@click": f"(() => {{ const baseUrl='{reverse('mission_export_report')}'; const container=$event.currentTarget.closest('[x-id]'); const form=container?.querySelector('form'); if(!form) {{ window.location=baseUrl + window.location.search; return; }} const fd=new FormData(form); const params=new URLSearchParams(); for(const [k,v] of fd.entries()) params.append(k,v); const qs=params.toString(); window.location=baseUrl + (qs ? '?' + qs : ''); }})()",
                },
            ),
            *(
                [
                    TableAction(
                        label="Thêm mới",
                        icon="plus.svg",
                        icon_position=Button.IconPosition.LEFT,
                        variant=Button.Variant.FILLED,
                        disabled=False,
                        loading_text="Đang mở.",
                        extra_attributes={
                            "menu": {
                                "groups": [
                                    [
                                        {
                                            "label": "Thêm mới",
                                            "icon": "plus.svg",
                                            "extra_attributes": {
                                                "@click": '$dispatch("open-mission-create-modal")',
                                            },
                                        },
                                        {
                                            "label": "Thêm mới Excel",
                                            "icon": "plus.svg",
                                            "extra_attributes": {
                                                "@click": '$dispatch("open-mission-create-excel-modal")',
                                            },
                                        },
                                    ]
                                ],
                                "position": "right",
                            },
                        },
                    )
                ]
                if is_mission_admin
                else []
            ),
        ],
        row_actions=[
            TableRowAction(
                label="",
                icon=detail_row_icon,
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.OUTLINED,
                disabled=False,
                extra_attributes={
                    "@click": f"""$dispatch("modal:open", {{
                        url: "{_row_detail_modal_url_tpl}",
                        title: "Chi tiết nhiệm vụ",
                        ariaLabel: "Chi tiết nhiệm vụ"
                    }});""",
                    "title": detail_row_action_label,
                    "aria-label": detail_row_action_label,
                },
            ),
            *(
                [
                    TableRowAction(
                        label="",
                        icon="trash.svg",
                        icon_position=Button.IconPosition.LEFT,
                        variant=Button.Variant.FILLED,
                        disabled=False,
                        extra_attributes={
                            "@click": f"""$dispatch("modal:open", {{
                                url: "{_row_delete_confirm_modal_url_tpl}",
                                title: "Xóa nhiệm vụ",
                                ariaLabel: "Xóa nhiệm vụ",
                                closeEvent: "mission:success",
                            }});""",
                            "title": "Xóa",
                        },
                    )
                ]
                if is_mission_admin
                else []
            ),
        ],
        bulk_actions=[],
        show_ordinal=True,
    )

    context = table_ctx.to_response_context(queryset, transformer=transformer)

    context["title"] = ""
    context["header"] = ""
    context["breadcrumbs"] = f'<a href="{reverse("mission_list")}" class="hover:underline">Nhiệm vụ</a>'

    return context

@method_decorator(permission_required('app.view_mission'), name='dispatch')
class MissionListPageView(ListView):
    model = Mission
    template_name = "mission/mission.html"

    def get_context_data(self, **kwargs):
        return get_mission_table_context(self.request)


@method_decorator(permission_required('app.view_mission'), name='dispatch')
class MissionListPartialView(ListView):
    model = Mission
    template_name = "mission/mission_partial.html"

    def get_context_data(self, **kwargs):
        return get_mission_table_context(self.request)


def _mission_detail_status(mission: Mission) -> str:
    if mission.completed_date:
        return "completed"
    if (mission.progress or 0) > 0:
        return "in_progress"
    return "pending"


@require_GET
def mission_detail_partial(request, pk: str):
    mission = get_object_or_404(
        Mission.objects.filter(is_active=True)
        .select_related(
            "department",
            "directive_document",
            "directive_document__directive_level",
        )
        .prefetch_related("assignee_departments", "reports"),
        pk=pk,
    )

    detail_status = _mission_detail_status(mission)

    reports = []
    for r in mission.reports.all().order_by("-report_year", "-report_month").select_related("sent_by"):
        who = "—"
        if r.sent_by:
            who = (r.sent_by.get_full_name() or "").strip() or (r.sent_by.username or "—")
        reports.append(
            SimpleNamespace(
                period_label=f"{int(r.report_month):02d}/{int(r.report_year)}",
                has_report=bool((r.content or "").strip()) or bool(r.is_sent),
                content=r.content or "",
                updated_by=who,
                updated_at=r.updated_at.strftime("%d/%m/%Y %H:%M") if r.updated_at else "—",
            )
        )

    latest = mission.reports.order_by("-report_year", "-report_month").first()
    current_report_content = (latest.content or "") if latest else ""

    csrf_input = mark_safe(
        f'<input type="hidden" name="csrfmiddlewaretoken" value="{get_token(request)}">'
    )

    return render(
        request,
        "mission/mission_detail_drawer_partial.html",
        {
            "mission": mission,
            "reports": reports,
            "is_admin": request.user.is_staff,
            "can_update_report": True,
            "detail_status": detail_status,
            "current_report_content": current_report_content,
            "csrf_input": csrf_input,
        },
    )
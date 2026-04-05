from datetime import timedelta
from html import escape as html_escape

from django.shortcuts import render
from django.urls import path, reverse
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_GET
from django.utils import timezone

from app.models import Mission
from app.models.mission import MissionReport
from app.models.document import DirectiveDocument, DocumentType

from .detail import (
    mission_complete,
    mission_delete,
    mission_delete_table_modal,
    mission_detail_modal,
    mission_result_report_period_filter_options,
    mission_update,
    mission_report_update,
    mission_report_submit,
)
# from .views import MissionListPageView, MissionListPartialView, mission_detail_partial
from .list import MissionListPageView, MissionListPartialView

from .create import MissionCreateView
from .export import mission_export_report
from .excel_import import (
    mission_template_download,
    mission_excel_validate,
    mission_excel_validate_page,
    mission_excel_create,
)

from .run_task import (
    mission_run_task_api,
    mission_run_overdue_status_task_api,
)

@require_GET
def mission_list_api(request):
    qs = (
        Mission.objects.filter(is_active=True)
        .select_related("department", "owner")
        .prefetch_related("assignee_departments")
        .order_by("-created_at", "-code")
    )

    rows = [
        {
            "code": m.code,
            "name": m.name,
            "department": m.department.get_short_label() if m.department else None,
            "assignee_departments": [
                d.get_short_label() for d in m.assignee_departments.all()
            ],
            "owner": getattr(m.owner, "username", None),
            "start_date": m.start_date.isoformat() if m.start_date else None,
            "due_date": m.due_date.isoformat() if m.due_date else None,
            "completed_date": m.completed_date.isoformat() if m.completed_date else None,
            "progress": m.progress,
            # bỏ đoạn t.computed_status vì không có biến t ở đây
            "status": None,
            "status_label": None,
            "report_status": getattr(m, "report_status", None),
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }
        for m in qs
    ]

    return JsonResponse({"rows": rows, "total_count": qs.count()})


@require_GET
def mission_directive_document_all_options(request):
    """Toàn bộ văn bản chỉ đạo (kể cả đã hết hiệu lực), có thể lọc theo cấp."""
    directive_level_id = (request.GET.get("directive_level") or "").strip()
    qs = (
        DirectiveDocument.objects.select_related("directive_level", "type")
        .order_by("-issued_at", "code")
    )
    if directive_level_id.isdigit():
        qs = qs.filter(directive_level_id=int(directive_level_id))
    data = [{"value": str(item.pk), "label": str(item)} for item in qs]
    return JsonResponse(data, safe=False)


@require_GET
def mission_directive_document_options(request):
    directive_level_id = (request.GET.get("directive_level") or "").strip()
    document_type_id = (request.GET.get("document_type") or "").strip()
    include_code = (request.GET.get("include_code") or "").strip()
    # Mốc so sánh: ngày mai 00:00:00 (timezone-aware), sau đó quy về DateField bằng `.date()`.
    # Điều kiện valid_to < next_day_date tương đương "valid_to <= hôm nay".
    next_day_start = (timezone.now() + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    next_day_date = next_day_start.date()
    today_date = (next_day_start - timedelta(days=1)).date()

    qs = (
        DirectiveDocument.objects.select_related("directive_level", "type").order_by(
            "-issued_at", "code"
        )
    )

    if not directive_level_id.isdigit():
        return JsonResponse([], safe=False)

    qs = qs.filter(directive_level_id=int(directive_level_id))

    if document_type_id.isdigit():
        qs = qs.filter(type_id=int(document_type_id))

    # Chỉ lấy văn bản còn hiệu lực để chọn:
    # - đã bắt đầu hiệu lực: valid_from < mốc ngày mai 00:00:00
    # - chưa hết hiệu lực: valid_to >= hôm nay hoặc không có ngày kết thúc
    active_qs = qs.filter(
        valid_from__lt=next_day_date,
    ).filter(
        Q(valid_to__isnull=True) | Q(valid_to__gte=today_date)
    )

    data = [{"value": str(item.pk), "label": str(item)} for item in active_qs]

    # Trường hợp edit nhiệm vụ cũ: vẫn hiển thị văn bản hiện tại nếu đã hết hiệu lực,
    # nhưng đánh dấu disabled để không cho chọn lại.
    if include_code and not active_qs.filter(pk=include_code).exists():
        included = qs.filter(pk=include_code).first()
        if included and included.valid_to is not None and included.valid_to < today_date:
            data.append(
                {
                    "value": str(included.pk),
                    "label": f"{included} (Đã hết hiệu lực)",
                    "disabled": True,
                }
            )

    return JsonResponse(data, safe=False)


@require_GET
def mission_report_period_options(request):
    from django.utils import timezone

    today = timezone.localdate()
    current_ym = today.year * 100 + today.month

    raw_periods = (
        MissionReport.objects.all()
        .values("report_year", "report_month")
        .distinct()
    )

    periods: set[tuple[int, int]] = set()
    for p in raw_periods:
        y = int(p["report_year"])
        m = int(p["report_month"])
        if (y * 100 + m) <= current_ym:
            periods.add((y, m))

    periods.add((today.year, today.month))

    sorted_periods = sorted(periods, key=lambda ym: (ym[0], ym[1]), reverse=True)
    data = [
        {"value": f"{y:04d}-{m:02d}", "label": f"{m} - {y}"}
        for (y, m) in sorted_periods
    ]
    return JsonResponse(data, safe=False)


@require_GET
def mission_status_options(request):
    data = [
        {"value": code, "label": label}
        for code, label in MissionReport.MissionStatus.choices
    ]
    return JsonResponse(data, safe=False)


@require_GET
def mission_report_status_options(request):
    data = [{"value": code, "label": label} for code, label in MissionReport.Status.choices]
    return JsonResponse(data, safe=False)

@require_GET
def mission_document_type_options(request):
    # Loại văn bản chỉ đạo: chỉ hiển thị QD hoặc NĐ
    qs = DocumentType.objects.filter(code__in=["QD", "NĐ"]).order_by("name")
    data = [{"value": str(item.id), "label": item.name} for item in qs]
    return JsonResponse(data, safe=False)

urlpatterns = [
    path("", MissionListPageView.as_view(), name="mission_list"),
    path("partial/", MissionListPartialView.as_view(), name="mission_list_partial"),
    # path("<int:pk>/detail/", mission_detail_partial, name="mission_detail_partial"),

    # đổi int -> str vì Mission.pk = code
    path("<str:pk>/detail/modal/", mission_detail_modal, name="mission_detail_modal"),
    path("<str:pk>/delete/modal/", mission_delete_table_modal, name="mission_delete_table_modal"),
    path(
        "<str:pk>/options/result-report-periods/",
        mission_result_report_period_filter_options,
        name="mission_result_report_period_filter_options",
    ),
    path("<str:mission_id>/update/", mission_update, name="mission_update"),
    path("<str:mission_id>/delete/", mission_delete, name="mission_delete"),
    path("<str:mission_id>/complete/", mission_complete, name="mission_complete"),
    path("api/missions/", mission_list_api, name="mission_list_api"),

    # sửa chỗ này
    path("create/", MissionCreateView.as_view(), name="mission_create"),

    path(
        "options/directive-documents/all/",
        mission_directive_document_all_options,
        name="mission_directive_document_all_options",
    ),
    path("options/directive-documents/", mission_directive_document_options, name="mission_directive_document_options"),
    path("options/document-types/", mission_document_type_options, name="mission_document_type_options"),
    path("options/report-periods/", mission_report_period_options, name="mission_report_period_options"),
    path("options/status/", mission_status_options, name="mission_status_options"),
    path("options/report-status/", mission_report_status_options, name="mission_report_status_options"),
    path("download-template/", mission_template_download, name="mission_template_download"),
    path("excel/validate/", mission_excel_validate, name="mission_excel_validate"),
    path("excel/validate/page/", mission_excel_validate_page, name="mission_excel_validate_page"),
    path("excel/create/", mission_excel_create, name="mission_excel_create"),
    path("export-report/", mission_export_report, name="mission_export_report"),

    # report_id của MissionReport vẫn là int
    path("missions/report/<int:report_id>/update/", mission_report_update, name="mission_report_update"),

    # mission_id của Mission là code => str
    path("missions/<str:mission_id>/report/submit/", mission_report_submit, name="mission_report_submit"),
    path("run-task/", mission_run_task_api, name="mission_run_task"),
    path("run-overdue-status-task/", mission_run_overdue_status_task_api, name="mission_run_overdue_status_task"),
]
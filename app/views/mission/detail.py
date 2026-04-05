from datetime import date, datetime, time
from types import SimpleNamespace
from django.db.models import Q

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_GET, require_POST

from app.models import Mission
from app.models.department import UserProfile
from app.models.document import DirectiveDocument
from app.models.mission import MissionReport

from .create import MissionCreateView


def _truncate_words(text: str, limit: int = 20) -> tuple[str, bool]:
    text = (text or "").strip()
    if not text:
        return "", False

    words = text.split()
    if len(words) <= limit:
        return text, False

    return " ".join(words[:limit]) + " ...", True


def _mission_has_report_with_content(mission_id: str) -> bool:
    return MissionReport.objects.filter(
        mission_id=mission_id
    ).filter(
        Q(is_sent=True) |
        (Q(content__isnull=False) & ~Q(content__exact=""))
    ).exists()


def _is_system_admin(user) -> bool:
    return bool(getattr(user, "is_superuser", False))


def _user_belongs_to_mission_department(user, mission: Mission) -> bool:
    if not mission.department_id:
        return False
    user_dept_id = (
        UserProfile.objects.filter(user_id=user.pk)
        .values_list("department_id", flat=True)
        .first()
    )
    return user_dept_id is not None and user_dept_id == mission.department_id


def _can_complete_mission(user, mission: Mission) -> bool:
    return _is_system_admin(user) or _user_belongs_to_mission_department(user, mission)


def _forbidden_mission_json(message: str):
    return JsonResponse({"success": False, "message": message}, status=403)


def _get_report_deadline_date(report_year: int, report_month: int, cutoff_day: int = 10) -> date:
    """
    Báo cáo tháng M có hạn đến hết ngày cutoff_day của tháng M+1.
    VD: báo cáo tháng 3/2026 => hạn hết ngày 10/4/2026
    """
    if report_month == 12:
        return date(report_year + 1, 1, cutoff_day)
    return date(report_year, report_month + 1, cutoff_day)


def _get_report_deadline_datetime(report_year: int, report_month: int, cutoff_day: int = 10):
    deadline_date = _get_report_deadline_date(report_year, report_month, cutoff_day)
    naive = datetime.combine(deadline_date, time(23, 59, 59))
    return timezone.make_aware(naive, timezone.get_current_timezone())


def _get_current_reporting_period(today: date | None = None) -> tuple[int, int]:
    """
    Quy tắc:
    - Từ ngày 10 của tháng M đến hết ngày 9 của tháng M+1 => kỳ báo cáo là tháng M
    Ví dụ:
    - 09/04 => tháng 03
    - 10/04 => tháng 04
    - 27/03 => tháng 03
    """
    today = today or timezone.localdate()

    if today.day >= 10:
        return today.year, today.month

    if today.month == 1:
        return today.year - 1, 12

    return today.year, today.month - 1


def _format_remaining_time(deadline_dt):
    now = timezone.localtime()
    if now >= deadline_dt:
        return "đã hết hạn"

    total_seconds = int((deadline_dt - now).total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    return f"còn lại {days} ngày {hours} giờ {minutes} phút"


def _can_edit_mission_report(user, mission: Mission, report: MissionReport) -> bool:
    if _is_system_admin(user):
        return True

    if not _user_belongs_to_mission_department(user, mission):
        return False

    now = timezone.localtime()
    deadline = _get_report_deadline_datetime(int(report.report_year), int(report.report_month), 10)
    return now <= deadline


def _current_period_report_already_submitted(report: MissionReport | None) -> bool:
    """Đã gửi báo cáo cho kỳ tương ứng (có thời điểm gửi)."""
    return report is not None and report.sent_at is not None


def _can_submit_mission_report(user, mission: Mission, report_year: int, report_month: int) -> bool:
    if _is_system_admin(user):
        return True

    if not _user_belongs_to_mission_department(user, mission):
        return False

    now = timezone.localtime()
    deadline = _get_report_deadline_datetime(report_year, report_month, 10)
    return now <= deadline


def _resolve_submitted_status_value():
    """
    Cố gắng tìm 1 status đại diện cho 'đã gửi/đã có báo cáo'
    để không hard-code mù tên enum.
    """
    no_report_value = getattr(MissionReport.Status, "NO_REPORT", None)

    preferred_names = [
        "APPROVED",
        "NOT_SENT",
    ]

    for name in preferred_names:
        value = getattr(MissionReport.Status, name, None)
        if value is not None:
            return value

    try:
        field = MissionReport._meta.get_field("status")
        choices = [choice[0] for choice in field.choices]
        for value in choices:
            if value != no_report_value:
                return value
    except Exception:
        pass

    return None


def _build_mission_reports_for_modal(mission: Mission, user=None) -> list:
    current_year, current_month = _get_current_reporting_period()
    rows: list[SimpleNamespace] = []

    for r in mission.reports.all():
        content_stripped = (r.content or "").strip()
        content_preview, is_truncated = _truncate_words(content_stripped, 20)
        no_work = bool(r.no_work_generated)
        locked = bool(r.is_locked)

        if not content_stripped and not locked and not no_work:
            continue

        show_no_submit = r.status == MissionReport.Status.NO_REPORT
        has_report_activity = bool(content_stripped) or no_work

        who = ""
        if r.sent_by_id:
            u = r.sent_by
            who = (u.get_full_name() or "").strip() or (u.username or "")

        dt_display = ""
        if r.sent_at:
            dt_display = timezone.localtime(r.sent_at).strftime("%d/%m/%Y %H:%M")
        elif r.updated_at:
            dt_display = timezone.localtime(r.updated_at).strftime("%d/%m/%Y %H:%M")

        can_edit_report = bool(user) and _can_edit_mission_report(user, mission, r)

        rows.append(
            SimpleNamespace(
                mission_report_id=r.id,
                month=int(r.report_month),
                year=int(r.report_year),
                content=content_stripped,
                content_preview=content_preview,
                is_truncated=is_truncated,
                has_content=has_report_activity and not show_no_submit,
                show_no_submit_badge=show_no_submit,
                show_no_activity_message=no_work and not content_stripped,
                is_current=(
                    int(r.report_month) == current_month
                    and int(r.report_year) == current_year
                ),
                is_latest=False,
                can_view_detail=has_report_activity,
                can_copy=bool(content_stripped) or no_work,
                can_edit=can_edit_report,
                created_by=who,
                created_at_display=dt_display,
                edit_deadline_display=_get_report_deadline_date(
                    int(r.report_year), int(r.report_month), 10
                ).strftime("%d/%m/%Y"),
            )
        )

    if rows:
        rows[0].is_latest = True

    return rows


def _report_period_filter_options(rows: list) -> list[dict]:
    """Các kỳ (năm/tháng) có báo cáo hiển thị trong modal, mới nhất trước."""
    pairs = sorted({(int(r.year), int(r.month)) for r in rows}, reverse=True)
    return [
        {"value": f"{y}-{m:02d}", "label": f"Tháng {m:02d}/{y}"} for y, m in pairs
    ]


@login_required
@require_GET
def mission_result_report_period_filter_options(request, pk):
    """JSON cho select lọc kỳ báo cáo trong khối Kết quả thực hiện (có tìm kiếm)."""
    mission = get_object_or_404(
        Mission.objects.filter(is_active=True).prefetch_related(
            Prefetch(
                "reports",
                queryset=MissionReport.objects.select_related("sent_by", "mission").order_by(
                    "-report_year", "-report_month", "-created_at", "-id"
                ),
            ),
        ),
        pk=pk,
    )
    rows = _build_mission_reports_for_modal(mission, user=request.user)
    opts = _report_period_filter_options(rows)
    data = [{"value": "all", "label": "Tất cả tháng"}] + opts
    return JsonResponse(data, safe=False)


@login_required
def mission_detail_modal(request, pk):
    # Backward compatibility: if old UI still opens delete confirm via query param
    # (open_delete_confirm=1), serve the dedicated table delete modal instead.
    open_delete_confirm_raw = (request.GET.get("open_delete_confirm") or "").strip().lower()
    if open_delete_confirm_raw in {"1", "true", "on", "yes"}:
        return mission_delete_table_modal(request, pk)

    mission = get_object_or_404(
        Mission.objects.filter(is_active=True)
        .select_related(
            "department",
            "directive_document",
            "directive_document__directive_level",
        )
        .prefetch_related(
            "assignee_departments",
            Prefetch(
                "reports",
                queryset=MissionReport.objects.select_related("sent_by", "mission").order_by(
                    "-report_year", "-report_month", "-created_at", "-id"
                ),
            ),
        ),
        pk=pk,
    )

    csrf_input = mark_safe(
        f'<input type="hidden" name="csrfmiddlewaretoken" value="{get_token(request)}">'
    )

    assignees = list(mission.assignee_departments.all())
    has_report_content = _mission_has_report_with_content(mission.pk)
    is_admin = _is_system_admin(request.user)

    can_delete = is_admin and not has_report_content

    current_report_year, current_report_month = _get_current_reporting_period()
    current_report = (
        mission.reports.filter(
            report_year=current_report_year,
            report_month=current_report_month,
        )
        .order_by("-created_at")
        .first()
    )

    deadline_dt = _get_report_deadline_datetime(current_report_year, current_report_month, 10)

    mission_reports = _build_mission_reports_for_modal(mission, user=request.user)

    context = {
        "mission": mission,
        "assignee_departments": assignees,
        # Giữ kiểu int để match với `department_options` (JSON trả id dạng number).
        "assignee_department_value_ids": [d.id for d in assignees],
        "can_edit": is_admin,
        "can_delete": can_delete,
        "can_complete": _can_complete_mission(request.user, mission),
        "csrf_input": csrf_input,
        "mission_reports": mission_reports,

        "current_report_year": current_report_year,
        "current_report_month": current_report_month,
        "current_report_label": f"Tháng {current_report_month:02d}/{current_report_year}",
        "current_report_deadline_display": timezone.localtime(deadline_dt).strftime("%Hh%M ngày %d/%m/%Y"),
        "current_report_deadline_iso": timezone.localtime(deadline_dt).isoformat(),
        "current_report_remaining": _format_remaining_time(deadline_dt),
        "current_report_content": (current_report.content or "") if current_report else "",
        "current_report_no_report": bool(current_report.no_work_generated) if current_report else False,
        "current_period_report_submitted": _current_period_report_already_submitted(current_report),
        "can_submit_current_report": (not mission.completed_date) and _can_submit_mission_report(
            request.user, mission, current_report_year, current_report_month
        ),
    }
    return render(request, "mission/mission_detail_modal.html", context)


@login_required
@require_GET
def mission_delete_table_modal(request, pk: str):
    mission = get_object_or_404(Mission.objects.filter(is_active=True), pk=pk)

    has_report_content = _mission_has_report_with_content(mission.code)
    is_admin = _is_system_admin(request.user)
    can_delete = is_admin and not has_report_content

    csrf_input = mark_safe(
        f'<input type="hidden" name="csrfmiddlewaretoken" value="{get_token(request)}">'
    )

    return render(
        request,
        "mission/mission_delete_table_modal.html",
        {
            "mission": mission,
            "can_delete": can_delete,
            "csrf_input": csrf_input,
        },
    )


def _resolve_latest_report_mission_status(mission: Mission) -> str:
    """
    Xác định mission_status cho báo cáo tháng gần nhất của mission
    dựa trên:
    - mission.due_date
    - có tồn tại báo cáo đã gửi ở các tháng trước hay không
      (điều kiện: sent_at IS NOT NULL)
    """
    today = timezone.localdate()
    is_late = bool(mission.due_date and today > mission.due_date)

    has_previous_submitted_report = MissionReport.objects.filter(
        mission_id=mission.pk,
        sent_at__isnull=False,
    ).exists()

    if has_previous_submitted_report:
        return (
            MissionReport.MissionStatus.IN_PROGRESS_LATE
            if is_late
            else MissionReport.MissionStatus.IN_PROGRESS_ON_TIME
        )

    return (
        MissionReport.MissionStatus.NOT_COMPLETED_LATE
        if is_late
        else MissionReport.MissionStatus.NOT_COMPLETED_ON_TIME
    )

@login_required
@require_POST
def mission_update(request, mission_id):
    if not _is_system_admin(request.user):
        return _forbidden_mission_json("Chỉ quản trị viên hệ thống được chỉnh sửa nhiệm vụ.")

    mission = get_object_or_404(Mission.objects.filter(is_active=True), pk=mission_id)
    v = MissionCreateView()

    try:
        directive_level_id = v._parse_required_int(
            request.POST.get("directive_level"),
            "Cấp chỉ đạo",
        )
        directive_document_pk = (request.POST.get("directive_document") or "").strip()
        if not directive_document_pk:
            raise ValueError("Văn bản chỉ đạo là bắt buộc.")
        doc = (
            DirectiveDocument.objects.filter(pk=directive_document_pk)
            .select_related("directive_level")
            .first()
        )
        if not doc:
            raise ValueError("Văn bản chỉ đạo không tồn tại.")
        if doc.directive_level_id != directive_level_id:
            raise ValueError("Văn bản chỉ đạo không thuộc cấp chỉ đạo đã chọn.")

        name = (request.POST.get("name") or "").strip()
        start_date = v._parse_required_date(
            request.POST.get("start_date"),
            "Ngày bắt đầu",
        )
        due_date = v._parse_optional_date(
            request.POST.get("due_date"),
            "Hạn xử lý",
        )
        completed_date_raw = (request.POST.get("completed_date") or "").strip()

        if mission.completed_date:
            completed_date = v._parse_required_date(completed_date_raw, "Ngày hoàn thành") if completed_date_raw else None
        else:
            completed_date = None

        department_id = v._parse_required_int(
            request.POST.get("department"),
            "Đơn vị chủ trì",
        )

        assignee_values = request.POST.getlist("assignee_departments")
        if assignee_values:
            assignee_department_ids = v._parse_list_int(
                assignee_values,
                "Đơn vị thực hiện",
            )
        else:
            assignee_department_ids = v._parse_json_list_int(
                request.POST.get("assignee_departments"),
                "Đơn vị thực hiện",
            )

        validated = v._validate_data(
            name=name,
            start_date=start_date,
            due_date=due_date,
            department_id=department_id,
            assignee_department_ids=assignee_department_ids,
        )

        with transaction.atomic():
            mission.name = name
            mission.start_date = start_date
            mission.due_date = due_date
            mission.department = validated["department"]
            mission.directive_document_id = directive_document_pk
            mission.updated_by_id = request.user.id
            mission.completed_date = completed_date
            mission.save()
            mission.assignee_departments.set(validated["assignee_departments"])
            latest_report = (
                MissionReport.objects.select_for_update()
                .filter(mission_id=mission.pk)
                .order_by("-report_year", "-report_month", "-created_at", "-id")
                .first()
            )

            if latest_report is not None:
                latest_report.mission_status = _resolve_latest_report_mission_status(mission)
                latest_report.save(update_fields=["mission_status", "updated_at"])

        return JsonResponse({"success": True})

    except ValueError as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@require_POST
def mission_report_submit(request, mission_id):
    mission = get_object_or_404(
        Mission.objects.filter(is_active=True).prefetch_related("reports"),
        pk=mission_id,
    )

    if mission.completed_date:
        return JsonResponse(
            {
                "success": False,
                "message": "Nhiệm vụ đã hoàn thành nên không thể cập nhật báo cáo.",
            },
            status=400,
        )

    report_year, report_month = _get_current_reporting_period()

    if not _can_submit_mission_report(request.user, mission, report_year, report_month):
        deadline = _get_report_deadline_datetime(report_year, report_month, 10)
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Bạn không có quyền cập nhật hoặc đã quá hạn báo cáo kỳ này "
                    f"({timezone.localtime(deadline).strftime('%H:%M %d/%m/%Y')})."
                ),
            },
            status=403,
        )

    content = (request.POST.get("content") or "").strip()
    no_report = str(request.POST.get("no_report") or "").lower() in {"1", "true", "on", "yes"}

    if not no_report and not content:
        return JsonResponse(
            {
                "success": False,
                "message": "Vui lòng nhập nội dung báo cáo hoặc chọn không phát sinh báo cáo.",
            },
            status=400,
        )

    try:
        submitted_status = _resolve_submitted_status_value()

        with transaction.atomic():
            report = (
                MissionReport.objects.select_for_update()
                .filter(
                    mission_id=mission.pk,
                    report_year=report_year,
                    report_month=report_month,
                )
                .order_by("-created_at", "-id")
                .first()
            )

            if _current_period_report_already_submitted(report):
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Báo cáo kỳ này đã được gửi.",
                    },
                    status=400,
                )

            is_new = report is None
            if is_new:
                report = MissionReport(
                    mission=mission,
                    report_year=report_year,
                    report_month=report_month,
                )

            today = timezone.localdate()

            # dữ liệu báo cáo
            report.content = "" if no_report else content
            report.no_work_generated = bool(no_report)
            report.is_locked = True
            report.sent_by = request.user
            report.sent_at = timezone.now()

            # nếu đã submit thì coi là đã gửi
            report.is_sent = True

            # trạng thái gửi báo cáo
            if submitted_status is not None:
                report.status = submitted_status

            # mission_status theo rule mới:
            # - chưa hoàn thành + chưa đến hạn (nếu có due_date) => IN_PROGRESS_ON_TIME
            # - chưa hoàn thành + quá hạn (nếu có due_date) => IN_PROGRESS_LATE
            today = timezone.localdate()

            if mission.due_date and today > mission.due_date:
                report.mission_status = MissionReport.MissionStatus.IN_PROGRESS_LATE
            else:
                report.mission_status = MissionReport.MissionStatus.IN_PROGRESS_ON_TIME

            if is_new:
                report.save()
            else:
                update_fields = [
                    "content",
                    "no_work_generated",
                    "is_locked",
                    "is_sent",
                    "sent_by",
                    "sent_at",
                    "status",
                    "mission_status",
                    "updated_at",
                ]
                report.save(update_fields=list(dict.fromkeys(update_fields)))

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Gửi báo cáo thành công."
                    if not no_report
                    else "Đã lưu trạng thái không phát sinh báo cáo."
                ),
                "report_id": report.id,
                "report_month": report_month,
                "report_year": report_year,
                "mission_status": report.mission_status,
                "status": report.status,
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

@login_required
@require_POST
def mission_report_update(request, report_id):
    report = get_object_or_404(
        MissionReport.objects.select_related("mission"),
        pk=report_id,
    )
    mission = report.mission

    if not _can_edit_mission_report(request.user, mission, report):
        deadline = _get_report_deadline_date(int(report.report_year), int(report.report_month), 10)
        return JsonResponse(
            {
                "success": False,
                "message": f"Bạn không có quyền sửa báo cáo này hoặc đã quá hạn chỉnh sửa ({deadline.strftime('%d/%m/%Y')}).",
            },
            status=403,
        )

    content = (request.POST.get("content") or "").strip()
    if not content:
        return JsonResponse(
            {"success": False, "message": "Nội dung báo cáo không được để trống."},
            status=400,
        )

    try:
        submitted_status = _resolve_submitted_status_value()
        update_fields = [
            "content",
            "no_work_generated",
            "is_locked",
            "is_sent",
            "sent_by",
            "sent_at",
            "updated_at",
        ]

        with transaction.atomic():
            report.content = content
            report.no_work_generated = False
            report.is_locked = True
            report.is_sent = True
            report.sent_by_id = request.user.id
            report.sent_at = timezone.now()

            if submitted_status is not None:
                report.status = submitted_status
                update_fields.append("status")

            report.save(update_fields=list(dict.fromkeys(update_fields)))

        return JsonResponse(
            {
                "success": True,
                "message": "Cập nhật báo cáo thành công.",
                "report_id": report.id,
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@require_POST
def mission_delete(request, mission_id):
    if not _is_system_admin(request.user):
        return _forbidden_mission_json("Chỉ quản trị viên hệ thống được xóa nhiệm vụ.")

    mission = get_object_or_404(Mission.objects.filter(is_active=True), pk=mission_id)

    if _mission_has_report_with_content(mission.code):
        return JsonResponse(
            {
                "success": False,
                "message": "Không thể xóa nhiệm vụ đã có báo cáo (đã nhập nội dung).",
            },
            status=400,
        )

    try:
        with transaction.atomic():
            mission.assignee_departments.clear()
            mission.delete()

        messages.success(request, "Đã xóa nhiệm vụ.")
        return JsonResponse({"success": True, "message": "Đã xóa nhiệm vụ."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@require_POST
def mission_complete(request, mission_id):
    mission = get_object_or_404(Mission.objects.filter(is_active=True), pk=mission_id)

    if not _can_complete_mission(request.user, mission):
        return _forbidden_mission_json(
            "Chỉ quản trị viên hệ thống hoặc người thuộc đơn vị chủ trì mới được đánh dấu hoàn thành."
        )

    if mission.completed_date:
        d = mission.completed_date
        return JsonResponse(
            {
                "success": True,
                "completed_date": d.isoformat(),
                "completed_date_display": d.strftime("%d/%m/%Y"),
            }
        )

    try:
        with transaction.atomic():
            completed_date = timezone.localdate()

            mission.completed_date = completed_date
            mission.updated_by_id = request.user.id
            mission.save(update_fields=["completed_date", "updated_at", "updated_by"])

            latest_report = (
                MissionReport.objects.select_for_update()
                .filter(mission_id=mission.pk)
                .order_by("-report_year", "-report_month", "-created_at", "-id")
                .first()
            )

            if latest_report is not None:
                if mission.due_date:
                    if completed_date < mission.due_date:
                        latest_report.mission_status = MissionReport.MissionStatus.COMPLETED_ON_TIME
                    elif completed_date > mission.due_date:
                        latest_report.mission_status = MissionReport.MissionStatus.COMPLETED_LATE
                    else:
                        latest_report.mission_status = MissionReport.MissionStatus.COMPLETED_ON_TIME
                else:
                    latest_report.mission_status = MissionReport.MissionStatus.COMPLETED_ON_TIME

                latest_report.save(update_fields=["mission_status", "updated_at"])

        messages.success(request, "Đã đánh dấu hoàn thành nhiệm vụ.")
        d = mission.completed_date
        return JsonResponse(
            {
                "success": True,
                "completed_date": d.isoformat(),
                "completed_date_display": d.strftime("%d/%m/%Y"),
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)
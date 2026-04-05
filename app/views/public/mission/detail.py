from types import SimpleNamespace

from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View

from app.models import Mission
from app.models.mission import MissionReport


def _truncate_words(text: str, limit: int = 20) -> tuple[str, bool]:
    text = (text or "").strip()
    if not text:
        return "", False

    words = text.split()
    if len(words) <= limit:
        return text, False

    return " ".join(words[:limit]) + " ...", True


def _build_public_mission_reports(mission: Mission) -> list[SimpleNamespace]:
    rows: list[SimpleNamespace] = []

    reports = mission.reports.all().order_by("-report_year", "-report_month", "-created_at", "-id")

    for r in reports:
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
            dt_display = r.sent_at.strftime("%d/%m/%Y %H:%M")
        elif r.updated_at:
            dt_display = r.updated_at.strftime("%d/%m/%Y %H:%M")

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
                is_latest=False,
                created_by=who,
                created_at_display=dt_display,
            )
        )

    if rows:
        rows[0].is_latest = True

    return rows


class PublicMissionDetailView(View):
    template_name = "public/mission/detail.html"

    def get_context_data(self, **kwargs):
        mission_id = (self.request.GET.get("id") or "").strip()

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
            pk=mission_id,
        )

        assignees = list(mission.assignee_departments.all())

        fields = {
            "code": "Mã nhiệm vụ",
            "name": "Tên nhiệm vụ",
            "directive_level": "Cấp chỉ đạo",
            "directive_document": "Văn bản chỉ đạo",
            "start_date": "Ngày bắt đầu",
            "due_date": "Hạn xử lý",
            "completed_date": "Ngày hoàn thành",
            "department": "Đơn vị chủ trì",
            "assignee_departments": "Đơn vị thực hiện",
        }

        mission_dict = {
            "id": mission.pk,
            "code": mission.code,
            "name": mission.name or "--",
            "directive_level": (
                mission.directive_document.directive_level.name
                if mission.directive_document and mission.directive_document.directive_level
                else "--"
            ),
            "directive_document": mission.directive_document.code if mission.directive_document else "--",
            "start_date": mission.start_date.strftime("%d/%m/%Y") if mission.start_date else "--/--/----",
            "due_date": mission.due_date.strftime("%d/%m/%Y") if mission.due_date else "--/--/----",
            "completed_date": mission.completed_date.strftime("%d/%m/%Y") if mission.completed_date else "--/--/----",
            "department": mission.department.get_short_label() if mission.department else "--",
            "assignee_departments": ", ".join([d.get_short_label() for d in assignees]) if assignees else "--",
        }

        return {
            "mission": mission_dict,
            "fields": fields,
            "mission_reports": _build_public_mission_reports(mission),
        }

    def get(self, request, *args, **kwargs):
        mission_id = (request.GET.get("id") or "").strip()
        if not mission_id:
            response = HttpResponse()
            response["HX-Redirect"] = reverse("public_mission_list")
            return response

        return render(request, self.template_name, self.get_context_data(**kwargs))
from datetime import datetime

from django.contrib import messages
from django.db import transaction
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.contrib.auth.views import method_decorator
from django.contrib.auth.decorators import permission_required
from pydantic_core import from_json

from app.models.mission import Mission, Department, MissionReport
from app.models.document import DirectiveDocument
from app.models.period import Period


@method_decorator(permission_required('app.add_mission'), name='dispatch')
class MissionCreateView(View):
    def _generate_mission_code(self, *, department: Department) -> str:
        short = (getattr(department, "short_name", "") or "").strip()
        if not short:
            raise ValueError("Đơn vị chủ trì chưa có short name để sinh mã nhiệm vụ.")

        yy = timezone.localdate().year % 100
        prefix = f"{short}_{yy:02d}_"

        last = 0
        for code in (
            Mission.objects.filter(code__startswith=prefix)
            .values_list("code", flat=True)
            .order_by("-code")[:50]
        ):
            try:
                suffix = int(str(code).rsplit("_", 1)[-1])
            except Exception:
                continue
            if suffix > last:
                last = suffix
                break

        return f"{prefix}{last + 1:04d}"

    def _parse_required_int(self, value, field_label):
        value = (value or "").strip()
        if not value:
            raise ValueError(f"{field_label} là bắt buộc.")

        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field_label} không hợp lệ.")

    def _parse_json_list_int(self, value, field_label):
        value = (value or "").strip()
        if not value:
            return []

        try:
            parsed = from_json(value)
        except Exception:
            raise ValueError(f"{field_label} không hợp lệ.")

        if not isinstance(parsed, list):
            raise ValueError(f"{field_label} không hợp lệ.")

        try:
            return [int(item) for item in parsed]
        except Exception:
            raise ValueError(f"{field_label} không hợp lệ.")

    def _parse_list_int(self, values, field_label):
        if not values:
            return []

        if not isinstance(values, (list, tuple)):
            raise ValueError(f"{field_label} không hợp lệ.")

        cleaned = [str(v).strip() for v in values if str(v).strip() != ""]
        if not cleaned:
            return []

        try:
            return [int(v) for v in cleaned]
        except Exception:
            raise ValueError(f"{field_label} không hợp lệ.")

    def _parse_required_date(self, value, field_label):
        value = (value or "").strip()
        if not value:
            raise ValueError(f"{field_label} là bắt buộc.")

        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"{field_label} không đúng định dạng ngày.")

    def _parse_optional_date(self, value, field_label):
        value = (value or "").strip()
        if not value:
            return None

        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"{field_label} không đúng định dạng ngày.")

    def _validate_data(
        self,
        *,
        name,
        start_date,
        due_date,
        department_id,
        assignee_department_ids,
    ):
        if not name:
            raise ValueError("Nhiệm vụ là bắt buộc.")

        if due_date and due_date < start_date:
            raise ValueError("Hạn xử lý không được nhỏ hơn ngày bắt đầu.")

        if len(assignee_department_ids) != len(set(assignee_department_ids)):
            raise ValueError("Danh sách đơn vị thực hiện bị trùng.")

        department = Department.objects.filter(id=department_id).first()
        if not department:
            raise ValueError("Đơn vị chủ trì không tồn tại.")
        if department.type != Department.Type.CAP:
            raise ValueError("Đơn vị chủ trì phải là đơn vị cấp CAP.")

        assignee_departments = Department.objects.filter(
            id__in=set(assignee_department_ids)
        )

        if assignee_departments.count() != len(set(assignee_department_ids)):
            raise ValueError("Có đơn vị thực hiện không tồn tại.")

        return {
            "department": department,
            "assignee_departments": assignee_departments,
        }

    def _resolve_initial_mission_status(self, mission: Mission):
        today = timezone.localdate()
        if mission.due_date and mission.due_date < today:
            return MissionReport.MissionStatus.NOT_COMPLETED_LATE
        return MissionReport.MissionStatus.NOT_COMPLETED_ON_TIME

    def _resolve_report_periods(self, start_date):
        # """
        # Rule:
        # - day <= 10: tạo kỳ tháng trước + tháng hiện tại của start_date
        # - day > 10: chỉ tạo kỳ tháng hiện tại của start_date
        # """
        # current_year = int(start_date.year)
        # current_month = int(start_date.month)

        # periods = []

        # if start_date.day <= 10:
        #     if current_month == 1:
        #         prev_year = current_year - 1
        #         prev_month = 12
        #     else:
        #         prev_year = current_year
        #         prev_month = current_month - 1

        #     periods.append((prev_year, prev_month))

        # periods.append((current_year, current_month))
        # return periods
        return [(int(start_date.year), int(start_date.month))]

    def post(self, request, *args, **kwargs):
        try:
            directive_level_id = self._parse_required_int(
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
            start_date = self._parse_required_date(
                request.POST.get("start_date"),
                "Ngày bắt đầu",
            )
            due_date = self._parse_optional_date(
                request.POST.get("due_date"),
                "Hạn xử lý",
            )
            department_id = self._parse_required_int(
                request.POST.get("department"),
                "Đơn vị chủ trì",
            )

            assignee_values = request.POST.getlist("assignee_departments")
            if assignee_values:
                assignee_department_ids = self._parse_list_int(
                    assignee_values,
                    "Đơn vị thực hiện",
                )
            else:
                assignee_department_ids = self._parse_json_list_int(
                    request.POST.get("assignee_departments"),
                    "Đơn vị thực hiện",
                )

            validated = self._validate_data(
                name=name,
                start_date=start_date,
                due_date=due_date,
                department_id=department_id,
                assignee_department_ids=assignee_department_ids,
            )

            last_err: Exception | None = None
            mission: Mission | None = None

            for _ in range(5):
                try:
                    mission = Mission(
                        code=self._generate_mission_code(
                            department=validated["department"]
                        ),
                        name=name,
                        start_date=start_date,
                        due_date=due_date,
                        department=validated["department"],
                        directive_document_id=directive_document_pk,
                        created_by_id=request.user.id,
                        updated_by_id=request.user.id,
                    )
                    mission.save()
                    last_err = None
                    break
                except IntegrityError as e:
                    last_err = e

            if mission is None or last_err is not None:
                raise ValueError("Không thể sinh mã nhiệm vụ. Vui lòng thử lại.")

            mission.assignee_departments.set(validated["assignee_departments"])

            mission_status = self._resolve_initial_mission_status(mission)
            report_periods = self._resolve_report_periods(start_date)

            periods_map = {
                (p.year, p.month): p
                for p in Period.objects.filter(
                    year__in=list({year for year, _ in report_periods})
                )
            }

            for year, month in report_periods:
                period = periods_map.get((year, month))

                if period is None:
                    period = Period.objects.filter(year=year, month=month).first()

                MissionReport.objects.get_or_create(
                    mission=mission,
                    report_year=year,
                    report_month=month,
                    defaults={
                        "period": period,  # có thì gán, không thì None
                        "content": "",
                        "is_sent": False,
                        "sent_at": None,
                        "no_work_generated": False,
                        "is_locked": False,
                        "status": MissionReport.Status.NOT_SENT,
                        "mission_status": mission_status,
                    },
                )

            messages.success(request, "Thêm nhiệm vụ thành công.")
            response = JsonResponse(
                {
                    "success": True,
                    "created_periods": [
                        {"year": year, "month": month} for year, month in report_periods
                    ],
                }
            )
            response["HX-Trigger"] = "mission:success"
            return response

        except ValueError as e:
            transaction.set_rollback(True)
            messages.error(request, str(e))
            return JsonResponse(
                {
                    "success": False,
                    "message": str(e),
                },
                status=400,
            )

        except Exception as e:
            messages.error(request, f"Lỗi: {str(e)}")
            return JsonResponse(
                {
                    "success": False,
                    "message": str(e),
                },
                status=500,
            )
import os
from http import HTTPStatus
from datetime import date

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from app.models.department import Department
from app.models.department_report import DepartmentReport
from app.models.report import ReportPeriodMonth
from app.models.storage import Storage
from app.models.period import Period
from utils import minio


REPORT_TYPE_META = {
    "MONTH": {"label": "Báo cáo tháng", "required": True, "order": 1},
    "QUARTER": {"label": "Báo cáo quý", "required": True, "order": 2},
    "HALF_YEAR": {"label": "Báo cáo 6 tháng", "required": True, "order": 3},
    "NINE_MONTH": {"label": "Báo cáo 9 tháng", "required": True, "order": 4},
    "YEAR": {"label": "Báo cáo năm", "required": True, "order": 5},
}

def _department_queryset():
    return Department.objects.only("id", "name", "short_name").order_by("name")

def _get_department_by_id(department_id):
    if not department_id:
        return None
    return _department_queryset().filter(pk=department_id).first()

def _get_user_department(user):
    if not user or not user.is_authenticated:
        return None

    direct_department_id = getattr(user, "department_id", None)
    if direct_department_id:
        return _get_department_by_id(direct_department_id)

    profile = getattr(user, "profile", None)
    profile_department_id = getattr(profile, "department_id", None) if profile else None
    if profile_department_id:
        return _get_department_by_id(profile_department_id)

    if hasattr(user, "department") and getattr(user, "department", None):
         return _get_department_by_id(getattr(user.department, "id", None))

    if profile and getattr(profile, "department", None):
        return _get_department_by_id(getattr(profile.department, "id", None))

    return None


def _build_period_options(department_id=None):
    today = date.today()
    current_year = today.year
    current_month = today.month
    previous_year = current_year - 1

    report_qs = DepartmentReport.objects.all()
    if department_id:
        report_qs = report_qs.filter(department_id=department_id)

    oldest_previous_year_month = (
        report_qs.filter(report_year=previous_year)
        .order_by("month")
        .values_list("month", flat=True)
        .first()
    )

    options = []

    if oldest_previous_year_month:
        for month in range(int(oldest_previous_year_month), 13):
            options.append(
                {
                    "value": f"{previous_year}-{month:02d}",
                    "label": f"Tháng {month:02d}/{previous_year}",
                    "month": month,
                    "year": previous_year,
                }
            )

    for month in range(1, current_month + 1):
        options.append(
            {
                "value": f"{current_year}-{month:02d}",
                "label": f"Tháng {month:02d}/{current_year}",
                "month": month,
                "year": current_year,
            }
        )

    return options


def _resolve_selected_period(request, period_options):
    today = date.today()
    default_value = f"{today.year}-{today.month:02d}"

    selected_period = (request.GET.get("period") or "").strip()
    allowed_values = {item["value"] for item in period_options}

    if selected_period not in allowed_values:
        selected_period = default_value

    for item in period_options:
        if item["value"] == selected_period:
            return selected_period, item["month"], item["year"]

    return default_value, today.month, today.year


def department_report_period_options(request):
    user = request.user
    is_admin = bool(getattr(user, "is_superuser", False))
    user_department = _get_user_department(user)

    requested_department_id = request.GET.get("department_id")
    if is_admin:
        department_id = requested_department_id or None
    else:
        department_id = str(user_department.id) if user_department else None

    options = _build_period_options(department_id=department_id)
    data = [{"value": item["value"], "label": item["label"]} for item in options]
    return JsonResponse(data, safe=False)


def department_report_create_department_options(request):
    user = request.user
    is_admin = bool(getattr(user, "is_superuser", False))
    user_department = _get_user_department(user)

    if is_admin:
        qs = _department_queryset()
    elif user_department:
        qs = _department_queryset().filter(pk=user_department.pk)
    else:
        qs = Department.objects.none()

    data = []
    for item in qs:
        short_name = (getattr(item, "short_name", "") or "").strip()
        name = (item.name or "").strip()

        if short_name:
            label = f"{short_name} - {name}"
        else:
            label = name

        data.append({
            "value": str(item.id),
            "label": label
        })

    return JsonResponse(data, safe=False)


def create_report_modal(request):
    user = request.user
    is_admin = bool(getattr(user, "is_superuser", False))
    user_department = _get_user_department(user)

    requested_department_id = (request.GET.get("department_id") or "").strip()

    if is_admin:
        department_id = requested_department_id
    else:
        department_id = str(user_department.id) if user_department else ""

    department = None
    if department_id:
        department = get_object_or_404(_department_queryset(), pk=department_id)

    period_options = _build_period_options(department_id=department_id or None)
    selected_period_value, selected_month, selected_year = _resolve_selected_period(
        request=request,
        period_options=period_options,
    )

    period_rows = (
        ReportPeriodMonth.objects.filter(month=selected_month)
        .values_list("report_type", flat=True)
        .distinct()
    )

    report_items = []
    for report_type in period_rows:
        meta = REPORT_TYPE_META.get(report_type)
        if not meta:
            continue

        upload_url = (
            f"{reverse('department_report_upload_temp')}?report_type={report_type}"
            f"&month={selected_month}&year={selected_year}"
        )
        if department_id:
            upload_url += f"&department_id={department_id}"

        report_items.append(
            {
                "report_type": report_type,
                "label": meta["label"],
                "required": meta["required"],
                "order": meta["order"],
                "upload_url": upload_url,
            }
        )

    report_items.sort(key=lambda x: x["order"])

    context = {
        "department": department,
        "department_id": str(department.id) if department else "",
        "department_name": department.name if department else "",
        "is_admin": is_admin,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "selected_period_value": selected_period_value,
        "period_options": period_options,
        "report_items": report_items,
        "modal_url_base": reverse("department_report_create_modal"),
        "department_options_url": reverse("department_report_create_department_options"),
        "period_options_url": reverse("department_report_period_options"),
        "submit_url": reverse("department_report_submit"),
    }
    return render(request, "report/create_report_modal.html", context)


def _format_file_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _build_report_filename(department_code: str, report_type: str, month: int, year: int) -> str:
    department_code = (department_code or "").strip().upper()

    if report_type == "MONTH":
        suffix = f"BC_THANG{month}"
    elif report_type == "QUARTER":
        quarter = ((month - 1) // 3) + 1
        suffix = f"BC_QUY{quarter}"
    elif report_type == "HALF_YEAR":
        suffix = "BC_6THANG"
    elif report_type == "NINE_MONTH":
        suffix = "BC_9THANG"
    elif report_type == "YEAR":
        suffix = "BC_NAM"
    else:
        suffix = f"BC_{report_type}"

    return f"{department_code}_{suffix}_{year}.pdf"


def _resolve_department_code(department: Department) -> str:
    short_name = (getattr(department, "short_name", "") or "").strip()
    if short_name:
        return short_name
    name = (getattr(department, "name", "") or "").strip()
    return name or "DONVI"


def _has_submitted_reports(department, month, year) -> bool:
    if not department or not month or not year:
        return False

    return DepartmentReport.objects.filter(
        department=department,
        month=month,
        report_year=year,
    ).filter(
        status="SENT",
    ).exists()


def _get_existing_report(department, month, year, report_type):
    if not department or not month or not year or not report_type:
        return None

    return DepartmentReport.objects.filter(
        department=department,
        month=month,
        report_type=report_type,
        report_year=year,
    ).first()


@transaction.atomic
def department_report_upload_temp(request):
    if request.method != "POST":
        return JsonResponse(
            {"error": "Phương thức không hợp lệ"},
            status=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    user = request.user
    is_admin = bool(getattr(user, "is_superuser", False))
    user_department = _get_user_department(user)

    report_type = (request.GET.get("report_type") or request.POST.get("report_type") or "").strip().upper()
    month_raw = (request.GET.get("month") or request.POST.get("month") or "").strip()
    year_raw = (request.GET.get("year") or request.POST.get("year") or "").strip()
    department_id_raw = (request.GET.get("department_id") or request.POST.get("department_id") or "").strip()

    errors = {}

    if report_type not in REPORT_TYPE_META:
        errors["report_type"] = "Loại báo cáo không hợp lệ"

    try:
        month = int(month_raw)
        if month < 1 or month > 12:
            raise ValueError()
    except Exception:
        month = None
        errors["month"] = "Tháng không hợp lệ"

    try:
        year = int(year_raw)
        if year < 2000 or year > 3000:
            raise ValueError()
    except Exception:
        year = None
        errors["year"] = "Năm không hợp lệ"

    if is_admin:
        if not department_id_raw:
            errors["department_id"] = "Đơn vị là bắt buộc"
            department = None
        else:
            department = _get_department_by_id(department_id_raw)
            if not department:
                errors["department_id"] = "Đơn vị không tồn tại"
    else:
        department = user_department
        if not department:
            errors["department_id"] = "Không xác định được đơn vị người dùng"

    upload_file = request.FILES.get("file")
    if not upload_file:
        errors["file"] = "Vui lòng chọn file PDF"

    if upload_file:
        _, ext = os.path.splitext(upload_file.name or "")
        if ext.lower() != ".pdf":
            errors["file"] = "Chỉ chấp nhận file PDF"
        if upload_file.size > 20 * 1024 * 1024:
            errors["file"] = "Dung lượng file tối đa 20MB"

    if errors:
        return JsonResponse({"errors": errors}, status=HTTPStatus.UNPROCESSABLE_ENTITY)

    final_file_name = _build_report_filename(
        department_code=_resolve_department_code(department),
        report_type=report_type,
        month=month,
        year=year,
    )

    period = None
    try:
        period = Period.objects.filter(
            month=month,
            year=year
        ).first()
    except Exception:
        period = None

    try:
        storage = Storage(
            file_name=final_file_name,
            size=upload_file.size,
        )
        storage.save(user=request.user)

        minio.upload(upload_file, storage.object_uid)

        existing_report = _get_existing_report(
            department=department,
            month=month,
            year=year,
            report_type=report_type,
        )

        defaults = {
            "file": storage,
            "file_name": final_file_name,
            "status": "NOT_SENT",
            "sent_at": None,
            "is_locked": False,
            "period": period,
        }
        if existing_report and existing_report.status == "SENT":
            defaults["status"] = existing_report.status
            defaults["sent_at"] = existing_report.sent_at
            defaults["is_locked"] = existing_report.is_locked

        report, _created = DepartmentReport.objects.update_or_create(
            department=department,
            month=month,
            report_type=report_type,
            report_year=year,
            defaults=defaults,
        )

        return JsonResponse(
            {
                "ok": True,
                "file_id": str(storage.object_uid),
                "report_id": report.id,
                "file_name": final_file_name,
                "file_size_label": _format_file_size(upload_file.size),
                "report_type": report_type,
                "department_id": str(department.id),
                "department_code": _resolve_department_code(department),
                "month": month,
                "year": year,
                "status": report.status,
            },
            status=HTTPStatus.OK,
        )
    except Exception as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@transaction.atomic
def department_report_submit(request):
    if request.method != "POST":
        return JsonResponse(
            {"error": "Phương thức không hợp lệ"},
            status=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    user = request.user
    is_admin = bool(getattr(user, "is_superuser", False))
    user_department = _get_user_department(user)

    period = (request.POST.get("period") or "").strip()
    department_id_raw = (request.POST.get("department_id") or "").strip()
    report_types = request.POST.getlist("report_types[]")

    errors = {}

    try:
        year_str, month_str = period.split("-")
        year = int(year_str)
        month = int(month_str)
    except Exception:
        year = None
        month = None
        errors["period"] = "Kỳ báo cáo không hợp lệ"

    if is_admin:
        if not department_id_raw:
            errors["department_id"] = "Đơn vị là bắt buộc"
            department = None
        else:
            department = _get_department_by_id(department_id_raw)
            if not department:
                errors["department_id"] = "Đơn vị không tồn tại"
    else:
        department = user_department
        if not department:
            errors["department_id"] = "Không xác định được đơn vị người dùng"

    expected_types = list(
        ReportPeriodMonth.objects.filter(month=month or 0)
        .values_list("report_type", flat=True)
        .distinct()
    )
    expected_types = [rt for rt in expected_types if rt in REPORT_TYPE_META]

    if not report_types:
        errors["report_types"] = "Chưa có báo cáo nào được tải lên"
    else:
        report_types = list(dict.fromkeys(report_types))
        missing_required_types = [rt for rt in expected_types if rt not in report_types]
        if missing_required_types:
            errors["report_types"] = (
                "Vui lòng tải lên đầy đủ tất cả loại báo cáo: "
                + ", ".join(missing_required_types)
            )

    if errors:
        return JsonResponse({"errors": errors}, status=HTTPStatus.UNPROCESSABLE_ENTITY)

    if _has_submitted_reports(department=department, month=month, year=year):
        return JsonResponse(
            {"error": "Đơn vị đã nộp báo cáo cho kỳ này rồi"},
            status=HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    qs = DepartmentReport.objects.filter(
        department=department,
        month=month,
        report_year=year,
        report_type__in=report_types,
    )

    report_map = {item.report_type: item for item in qs}

    missing_types = [rt for rt in report_types if rt not in report_map]
    if missing_types:
        return JsonResponse(
            {"errors": {"report_types": f"Thiếu bản ghi báo cáo cho: {', '.join(missing_types)}"}},
            status=HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    now = timezone.now()
    qs.update(status="SENT", sent_at=now)

    return JsonResponse(
        {
            "ok": True,
            "message": "Gửi báo cáo thành công",
            "count": qs.count(),
        },
        status=HTTPStatus.OK,
    )

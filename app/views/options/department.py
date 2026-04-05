from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ...models.department import Department


def _quota_department_label(short_name: str | None, name: str | None) -> str:
    """Ví dụ: PA01 - Phòng A. Thiếu một phần thì chỉ hiển thị phần còn lại."""
    sn = (short_name or "").strip()
    nm = (name or "").strip()
    if sn and nm:
        if sn.casefold() == nm.casefold():
            return sn
        return f"{sn} - {nm}"
    return sn or nm


def _department_option_rows_from_queryset(qs) -> list[dict]:
    """Label thống nhất: short_name - name (qua _quota_department_label)."""
    return [
        {
            "value": row["id"],
            "label": _quota_department_label(row.get("short_name"), row.get("name"))
            or row["id"],
        }
        for row in qs.order_by("short_name", "name").values("id", "short_name", "name")
    ]


def _department_option_rows(*, scope: str, quota_id: str) -> list[dict]:
    """
    scope:
      - lead: chỉ CAP (đơn vị chủ trì nhiệm vụ)
      - report | assignee: toàn bộ đơn vị
      - (rỗng hoặc quota): có thể lọc theo quota_id
    Mọi nhánh: label = short_name - name (vd PA01 - Phòng A).
    """
    scope = (scope or "").strip().lower()
    quota_id = (quota_id or "").strip()

    if scope == "lead":
        return _department_option_rows_from_queryset(
            Department.objects.filter(type=Department.Type.CAP)
        )

    if scope in ("report", "assignee"):
        return _department_option_rows_from_queryset(Department.objects.all())

    qs = Department.objects.all()
    if quota_id.isdigit():
        qs = qs.filter(quota_reports__quota_id=int(quota_id)).distinct()
    return _department_option_rows_from_queryset(qs)


@require_GET
def department_options(request):
    """
    Mặc định (quota/dashboard): label dạng short_name - name.
    GET scope / quota_id: xem _department_option_rows.
    """
    scope = (request.GET.get("scope") or "").strip().lower()
    quota_id = (request.GET.get("quota_id") or "").strip()
    rows = _department_option_rows(scope=scope, quota_id=quota_id)
    return JsonResponse(rows, safe=False)


@require_GET
def department_report_department_options(request):
    """URL cũ: tương đương scope=report."""
    rows = _department_option_rows(scope="report", quota_id="")
    return JsonResponse(rows, safe=False)


@require_GET
def department_type_options(request):
    data = [
        {"value": value, "label": label}
        for value, label in Department.Type.choices
    ]
    return JsonResponse(data, safe=False)


@require_GET
def department_report_status_options(request):
    data = [
        {"value": "SENT", "label": "Đã gửi"},
        {"value": "NO_REPORT", "label": "Không gửi"},
    ]
    return JsonResponse(data, safe=False)


@require_GET
def department_report_type_options(request):
    data = [
        {"value": "MONTH", "label": "Báo cáo tháng"},
        {"value": "QUARTER", "label": "Báo cáo quý"},
        {"value": "HALF_YEAR", "label": "Báo cáo 6 tháng"},
        {"value": "NINE_MONTH", "label": "Báo cáo 9 tháng"},
        {"value": "YEAR", "label": "Báo cáo năm"},
    ]
    return JsonResponse(data, safe=False)

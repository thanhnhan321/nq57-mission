from django.db import transaction
from huey.contrib.djhuey import lock_task, task

from app.models import Department, DepartmentReport, Period, ReportPeriodMonth
from utils.log import logger


@task()
@lock_task("manual-create-monthly-department-reports")
def enqueue_create_department_reports(report_year: int, report_month: int):
    """
    Task manual để API gọi async qua Huey
    hoặc được create_new_period enqueue sau khi tạo period thành công.
    """
    return _create_department_reports_for_period(report_year, report_month)


def run_create_department_reports_sync(report_year: int, report_month: int):
    """
    Hàm chạy sync để API debug/test ngay lập tức.
    """
    return _create_department_reports_for_period(report_year, report_month)


def _create_department_reports_for_period(report_year: int, report_month: int):
    _validate_period(report_year, report_month)

    logger.info(
        f"Initializing department reports for {report_year}-{report_month:02d}..."
    )

    report_types = list(
        ReportPeriodMonth.objects.filter(month=report_month)
        .values_list("report_type", flat=True)
        .distinct()
    )

    if not report_types:
        logger.info(
            f"No report types configured in report_period_month for month={report_month}"
        )
        return {
            "created": 0,
            "skipped": False,
            "report_year": report_year,
            "report_month": report_month,
            "report_types": [],
            "departments": 0,
            "skipped_departments": 0,
            "message": (
                f"No report types configured for month {report_month:02d}/{report_year}"
            ),
        }

    department_qs = Department.objects.all().only("id", "name")

    department_ids = list(department_qs.values_list("id", flat=True))
    if not department_ids:
        logger.info("No departments found to initialize department reports")
        return {
            "created": 0,
            "skipped": False,
            "report_year": report_year,
            "report_month": report_month,
            "report_types": report_types,
            "departments": 0,
            "skipped_departments": 0,
            "message": "No departments found",
        }

    period, _ = Period.objects.get_or_create(
        year=report_year,
        month=report_month,
    )

    existing_department_ids = set(
        DepartmentReport.objects.filter(
            department_id__in=department_ids,
            month=report_month,
            report_year=report_year,
        ).values_list("department_id", flat=True)
    )

    reports = []
    skipped_departments = 0

    for department in department_qs:
        if department.id in existing_department_ids:
            skipped_departments += 1
            continue

        for report_type in report_types:
            reports.append(
                DepartmentReport(
                    department=department,
                    month=report_month,
                    report_year=report_year,
                    report_type=report_type,
                    period=period,
                    status="NO_REPORT",
                    sent_at=None,
                    is_locked=False,
                    file=None,
                    file_name=None,
                    note=None,
                )
            )

    if not reports:
        logger.info(
            f"No new department reports to create for {report_year}-{report_month:02d}"
        )
        return {
            "created": 0,
            "skipped": False,
            "report_year": report_year,
            "report_month": report_month,
            "report_types": report_types,
            "departments": len(department_ids),
            "skipped_departments": skipped_departments,
            "period_id": getattr(period, "id", None),
            "message": (
                f"No new department reports to create for "
                f"{report_year}-{report_month:02d}"
            ),
        }

    with transaction.atomic():
        DepartmentReport.objects.bulk_create(reports, batch_size=500)

    logger.info(
        f"Created {len(reports)} department reports for {report_year}-{report_month:02d}. "
        f"Skipped departments: {skipped_departments}"
    )

    return {
        "created": len(reports),
        "skipped": False,
        "report_year": report_year,
        "report_month": report_month,
        "report_types": report_types,
        "departments": len(department_ids),
        "skipped_departments": skipped_departments,
        "period_id": getattr(period, "id", None),
        "message": (
            f"Created {len(reports)} department reports for "
            f"{report_year}-{report_month:02d}"
        ),
    }


def _validate_period(report_year: int, report_month: int):
    if not isinstance(report_year, int):
        raise ValueError("report_year must be integer")
    if not isinstance(report_month, int):
        raise ValueError("report_month must be integer")
    if report_month < 1 or report_month > 12:
        raise ValueError("report_month must be between 1 and 12")
    if report_year < 2000 or report_year > 3000:
        raise ValueError("report_year is invalid")
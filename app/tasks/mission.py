from datetime import timedelta

from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from huey import crontab
from huey.contrib import djhuey
from huey.contrib.djhuey import lock_task, task, signal
from huey.signals import SIGNAL_CANCELED, SIGNAL_ERROR, SIGNAL_LOCKED, SIGNAL_REVOKED

import env
from app.models import Mission, MissionReport, Period
from utils.log import logger


@signal(SIGNAL_ERROR, SIGNAL_LOCKED, SIGNAL_CANCELED, SIGNAL_REVOKED)
def task_not_executed_handler(signal, task_instance, exc=None):
    logger.opt(exception=exc).error(
        f"Task {getattr(task_instance, 'name', task_instance.id)} not executed: {signal}"
    )


# =========================
# MONTHLY CREATE REPORTS
# =========================

@task()
@lock_task("manual-create-monthly-mission-reports")
def enqueue_create_mission_reports(report_year: int, report_month: int):
    """
    Task manual để API gọi async qua Huey
    hoặc được create_new_period enqueue sau khi tạo period thành công.
    """
    return _create_mission_reports_for_period(report_year, report_month)


def run_create_mission_reports_sync(report_year: int, report_month: int):
    """
    Hàm chạy sync để API debug/test ngay lập tức.
    """
    return _create_mission_reports_for_period(report_year, report_month)


def _create_mission_reports_for_period(report_year: int, report_month: int):
    """
    Logic dùng chung cho cả task async và API manual.
    """
    _validate_period(report_year, report_month)

    exists = MissionReport.objects.filter(
        report_year=report_year,
        report_month=report_month,
    ).exists()

    logger.info(
        "DEBUG monthly mission reports: count=%s, ids=%s",
        exists.count(),
        list(exists.values_list("mission_id", flat=True)),
    )

    if exists and not env.IS_LOCAL:
        logger.info(
            f"Mission reports for {report_year}-{report_month:02d} already initialized"
        )
        return {
            "created": 0,
            "skipped": True,
            "message": f"Mission reports for {report_year}-{report_month:02d} already initialized",
        }

    logger.info(f"Initializing mission reports for {report_year}-{report_month:02d}...")

    mission_qs = (
        Mission.objects.filter(is_active=True)
        .filter(completed_date__isnull=True)
        .only("code", "due_date", "completed_date", "is_active", "start_date")
    )

    mission_codes = list(mission_qs.values_list("code", flat=True))
    if not mission_codes:
        logger.info(f"No missions eligible for {report_year}-{report_month:02d}")
        return {
            "created": 0,
            "skipped": False,
            "message": f"No missions eligible for {report_year}-{report_month:02d}",
        }

    existing_codes = set(
        MissionReport.objects.filter(
            mission_id__in=mission_codes,
            report_year=report_year,
            report_month=report_month,
        ).values_list("mission_id", flat=True)
    )

    reports = []
    for mission in mission_qs:
        if mission.code in existing_codes:
            continue

        reports.append(
            MissionReport(
                mission=mission,
                report_year=report_year,
                report_month=report_month,
                content=None,
                is_sent=False,
                sent_at=None,
                no_work_generated=False,
                is_locked=False,
                status=MissionReport.Status.NOT_SENT,
                mission_status=_resolve_initial_mission_status(
                    mission=mission,
                    report_year=report_year,
                    report_month=report_month,
                ),
            )
        )

    if not reports:
        logger.info(f"No new mission reports to create for {report_year}-{report_month:02d}")
        return {
            "created": 0,
            "skipped": False,
            "message": f"No new mission reports to create for {report_year}-{report_month:02d}",
        }

    with transaction.atomic():
        MissionReport.objects.bulk_create(reports, batch_size=500)

    logger.info(
        f"Created {len(reports)} mission reports for {report_year}-{report_month:02d}"
    )

    return {
        "created": len(reports),
        "skipped": False,
        "message": f"Created {len(reports)} mission reports for {report_year}-{report_month:02d}",
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


def _resolve_initial_mission_status(
    mission: Mission,
    report_year: int,
    report_month: int,
):
    today = timezone.localdate()

    has_previous_submitted_report = MissionReport.objects.filter(
        mission_id=mission.code,
        sent_at__isnull=False,
    ).filter(
        Q(report_year__lt=report_year) |
        Q(report_year=report_year, report_month__lt=report_month)
    ).exists()

    is_late = bool(mission.due_date and today > mission.due_date)

    if has_previous_submitted_report:
        if is_late:
            return MissionReport.MissionStatus.IN_PROGRESS_LATE
        return MissionReport.MissionStatus.IN_PROGRESS_ON_TIME

    if is_late:
        return MissionReport.MissionStatus.NOT_COMPLETED_LATE

    return MissionReport.MissionStatus.NOT_COMPLETED_ON_TIME


# =========================
# DAILY OVERDUE STATUS UPDATE
# =========================

@task()
@lock_task("manual-update-mission-overdue-status-daily")
def enqueue_update_mission_overdue_status_for_date(base_date_str: str = None):
    """
    API async gọi vào đây.
    base_date_str format: YYYY-MM-DD
    Nếu không truyền thì mặc định ngày hiện tại.
    """
    base_date = _parse_base_date_or_today(base_date_str)
    return _update_mission_overdue_status_for_date(base_date)


def run_update_mission_overdue_status_sync(base_date_str: str = None):
    """
    API sync gọi vào đây để chạy ngay.
    """
    base_date = _parse_base_date_or_today(base_date_str)
    return _update_mission_overdue_status_for_date(base_date)


def _parse_base_date_or_today(base_date_str: str = None):
    if not base_date_str:
        return timezone.localdate()

    try:
        return timezone.datetime.strptime(base_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("base_date must be in format YYYY-MM-DD")


@djhuey.db_periodic_task(crontab(hour="4", minute="0"))
@djhuey.lock_task("cron-update-mission-overdue-status-daily")
def cron_update_mission_overdue_status_daily():
    """
    Tự động chạy mỗi ngày lúc 04:00 sáng.
    """
    return _update_mission_overdue_status_for_date(timezone.localdate())


def _update_mission_overdue_status_for_date(base_date):
    target_due_date = base_date - timedelta(days=1)

    logger.info(
        f"Updating overdue mission status. base_date={base_date}, target_due_date={target_due_date}"
    )

    mission_qs = (
        Mission.objects.filter(
            is_active=True,
            completed_date__isnull=True,
            due_date=target_due_date,
        )
        .only("code", "due_date", "completed_date", "is_active")
    )

    mission_codes = list(mission_qs.values_list("code", flat=True))
    if not mission_codes:
        logger.info(
            f"No overdue missions found for target_due_date={target_due_date}"
        )
        return {
            "updated": 0,
            "checked": 0,
            "base_date": str(base_date),
            "target_due_date": str(target_due_date),
            "message": f"No overdue missions found for target_due_date={target_due_date}",
        }

    updated_count = 0
    checked_count = 0
    skipped_no_latest_report = 0

    with transaction.atomic():
        for mission in mission_qs:
            checked_count += 1

            latest_report = (
                MissionReport.objects.filter(mission_id=mission.code)
                .order_by("-report_year", "-report_month", "-created_at")
                .first()
            )

            if not latest_report:
                skipped_no_latest_report += 1
                continue

            has_any_submitted_report = MissionReport.objects.filter(
                mission_id=mission.code,
                sent_at__isnull=False,
            ).exists()

            new_status = None

            if mission.completed_date is None:
                if has_any_submitted_report:
                    new_status = MissionReport.MissionStatus.IN_PROGRESS_LATE
                else:
                    new_status = MissionReport.MissionStatus.NOT_COMPLETED_LATE

            if new_status and latest_report.mission_status != new_status:
                latest_report.mission_status = new_status
                latest_report.save(update_fields=["mission_status", "updated_at"])
                updated_count += 1

    logger.info(
        f"Updated overdue mission status done. "
        f"base_date={base_date}, target_due_date={target_due_date}, "
        f"checked={checked_count}, updated={updated_count}, skipped_no_latest_report={skipped_no_latest_report}"
    )

    return {
        "updated": updated_count,
        "checked": checked_count,
        "skipped_no_latest_report": skipped_no_latest_report,
        "base_date": str(base_date),
        "target_due_date": str(target_due_date),
        "message": (
            f"Checked {checked_count} missions, updated {updated_count} latest reports "
            f"for target_due_date={target_due_date}"
        ),
    }

@task()
@lock_task("manual-update-mission-report-period")
def enqueue_update_mission_report_period(report_year: int, report_month: int):
    """
    Task async:
    - quét mission_report
    - lấy các report chưa có period_id
    - chỉ xử lý report có report_year/report_month đúng kỳ truyền vào
    - dò Period để gán period_id; nếu không có Period thì set null
    """
    return _update_mission_report_period(report_year, report_month)


def run_update_mission_report_period_sync(report_year: int, report_month: int):
    """
    Hàm sync để API debug/test chạy ngay.
    """
    return _update_mission_report_period(report_year, report_month)


def _update_mission_report_period(report_year: int, report_month: int):
    _validate_period(report_year, report_month)

    logger.info(
        f"Updating mission_report.period_id for {report_year}-{report_month:02d}"
    )

    period = (
        Period.objects.filter(year=report_year, month=report_month)
        .only("id")
        .first()
    )

    if not period:
        logger.info(
            f"No period found for {report_year}-{report_month:02d}, skip updating mission_report"
        )
        return {
            "updated": 0,
            "checked": 0,
            "period_id": None,
            "report_year": report_year,
            "report_month": report_month,
            "message": (
                f"No period found for {report_year}-{report_month:02d}, skip update"
            ),
        }
    target_period_id = period.id if period else None

    report_qs = MissionReport.objects.filter(
        period_id__isnull=True,
        report_year=report_year,
        report_month=report_month,
    )

    checked = report_qs.count()

    if checked == 0:
        logger.info(
            f"No mission reports need period update for {report_year}-{report_month:02d}"
        )
        return {
            "updated": 0,
            "checked": 0,
            "period_id": target_period_id,
            "report_year": report_year,
            "report_month": report_month,
            "message": (
                f"No mission reports need period update for "
                f"{report_year}-{report_month:02d}"
            ),
        }

    with transaction.atomic():
        updated = report_qs.update(period_id=target_period_id)

    logger.info(
        f"Updated mission_report.period_id done. "
        f"year={report_year}, month={report_month}, "
        f"checked={checked}, updated={updated}, period_id={target_period_id}"
    )

    return {
        "updated": updated,
        "checked": checked,
        "period_id": target_period_id,
        "report_year": report_year,
        "report_month": report_month,
        "message": (
            f"Checked {checked} mission reports, updated {updated} records "
            f"for {report_year}-{report_month:02d}"
        ),
    }
from django.core.cache import cache
from django.utils.timezone import datetime
from django.db import transaction
from huey import crontab
from huey.contrib import djhuey
from huey.signals import SIGNAL_CANCELED, SIGNAL_ERROR, SIGNAL_LOCKED, SIGNAL_REVOKED

from app.models.quota import QuotaAssignment
import env
from ..models import Period, Quota, QuotaReport
from ..handlers.period import get_latest_period, LATEST_PERIOD_KEY, PERIODS_KEY
from utils.log import logger

from .mission import *
from .department_report import *

@djhuey.signal(SIGNAL_ERROR, SIGNAL_LOCKED, SIGNAL_CANCELED, SIGNAL_REVOKED)
def task_not_executed_handler(signal, task_instance, exc=None):
   logger.opt(exception=exc).error(f"Task {getattr(task_instance, 'name', task_instance.id)} not executed: {signal}")

# production config 0 0 1 * *
# local config * * * * *
cron = { 'minute': '0' } if env.IS_LOCAL else {'minute': '0', 'hour': '0', 'day': '1'}
@djhuey.db_periodic_task(crontab(**cron))
@djhuey.lock_task('cron-create-new-period')
def create_new_period():
    latest_period = get_latest_period()
    now = datetime.now()
    if latest_period and latest_period.year == now.year and latest_period.month == now.month:
        logger.info(f"Period {now.year}-{now.month:02d} already exists")
        return {
            "created": False,
            "year": now.year,
            "month": now.month,
            "message": f"Period {now.year}-{now.month:02d} already exists",
        }

    logger.info("Initializing period...")
    with transaction.atomic():
        period = Period(year=now.year, month=now.month)
        period.save()

        cache.delete(LATEST_PERIOD_KEY)
        cache.delete(PERIODS_KEY)

    logger.info(f"Created new period {period.year}-{period.month}")

    quota_task = create_new_quota_reports()
    mission_task = enqueue_create_mission_reports(period.year, period.month)
    mission_report_period_task = enqueue_update_mission_report_period(period.year, period.month)
    department_report_task = enqueue_create_department_reports(period.year, period.month)

    logger.info(
        f"Queued follow-up tasks for period {period.year}-{period.month:02d}: "
        f"quota={getattr(quota_task, 'id', None)}, "
        f"mission={getattr(mission_task, 'id', None)}, "
        f"mission_report_period={getattr(mission_report_period_task, 'id', None)}, "
        f"department_report={getattr(department_report_task, 'id', None)}"
    )

    return {
        "created": True,
        "year": period.year,
        "month": period.month,
        "period_id": getattr(period, "id", None),
        "quota_task_id": str(getattr(quota_task, "id", "")),
        "mission_task_id": str(getattr(mission_task, "id", "")),
        "mission_report_period_task_id": str(getattr(mission_report_period_task, "id", "")),
        "department_report_task_id": str(getattr(department_report_task, "id", "")),
        "message": f"Created new period {period.year}-{period.month:02d} and queued follow-up tasks",
    }


@djhuey.on_commit_task()
def create_new_quota_reports():
    logger.info("Creating new quota reports...")
    latest_period = get_latest_period()
    first_day_of_period = datetime(latest_period.year, latest_period.month, 1)
    active_quotas = list(
        Quota.objects
        .prefetch_related('department_assignments')
        .filter(
            expired_at__gte=first_day_of_period
        )
        .values('id', 'type')
    )
    cumulative_quota_ids = set(quota['id'] for quota in active_quotas if quota['type'] == Quota.Type.CUMULATIVE)
    department_ids = set()
    quota_dept_report_map = {}
    for assignment in QuotaAssignment.objects.filter(quota__in=active_quotas).values('quota_id', 'department_id'):
        quota_dept_report_map[assignment['quota_id']][assignment['department_id']] = None
        department_ids.add(assignment['department_id'])
    last_reports = (
        QuotaReport.objects
        .filter(
            quota_id__in=cumulative_quota_ids,
            department_id__in=department_ids,
            expected_value__isnull=False,
        )
        .order_by('-period_id')
        .distinct('quota_id', 'department_id')
        .values('id','quota_id', 'department_id', 'expected_value', 'actual_value')
    )
    for report in last_reports:
        quota_dept_report_map[report['quota_id']][report['department_id']] = report
    reports = []
    for quota_id, dept_report_map in quota_dept_report_map.items():
        for department_id, last_report in dept_report_map.items():
            report = QuotaReport(
                quota_id=quota_id,
                department_id=department_id,
                period=latest_period,
                status=QuotaReport.Status.NOT_SENT,
                previous_report_id=last_report['id'] if last_report else None,
                expected_value=last_report['expected_value'] if last_report else None,
                actual_value=last_report['actual_value'] if last_report else None,
            )
            reports.append(report)
    with transaction.atomic():
        QuotaReport.objects.bulk_create(reports)
        logger.info(f"Created {len(reports)} new quota reports for period {latest_period.year}-{latest_period.month}")

from django.core.cache import cache
from django.utils.timezone import datetime
from django.db import transaction
from huey import crontab
from huey.contrib import djhuey
from huey.signals import SIGNAL_CANCELED, SIGNAL_ERROR, SIGNAL_LOCKED, SIGNAL_REVOKED

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
    department_report_task = enqueue_create_department_reports(period.year, period.month)

    logger.info(
        f"Queued follow-up tasks for period {period.year}-{period.month:02d}: "
        f"quota={getattr(quota_task, 'id', None)}, "
        f"mission={getattr(mission_task, 'id', None)}, "
        f"department_report={getattr(department_report_task, 'id', None)}"
    )

    return {
        "created": True,
        "year": period.year,
        "month": period.month,
        "period_id": getattr(period, "id", None),
        "quota_task_id": str(getattr(quota_task, "id", "")),
        "mission_task_id": str(getattr(mission_task, "id", "")),
        "department_report_task_id": str(getattr(department_report_task, "id", "")),
        "message": f"Created new period {period.year}-{period.month:02d} and queued follow-up tasks",
    }


@djhuey.on_commit_task()
def create_new_quota_reports():
   logger.info("Creating new quota reports...")
   latest_period = get_latest_period()
   first_day_of_period = datetime(latest_period.year, latest_period.month, 1)
   active_quotas = (
      Quota.objects
      .prefetch_related('department_assignments')
      .filter(
         expired_at__gte=first_day_of_period
      )
      .all()
   )
   reports = []
   for quota in active_quotas:
      for assignment in quota.department_assignments.filter(is_leader=False).all():
         report = QuotaReport(
            quota=quota,
            department=assignment.department,
            period=latest_period,
            status=QuotaReport.Status.NOT_SENT,
         )
         reports.append(report)
   with transaction.atomic():
      QuotaReport.objects.bulk_create(reports)
      logger.info(f"Created {len(reports)} new quota reports for period {latest_period.year}-{latest_period.month}")

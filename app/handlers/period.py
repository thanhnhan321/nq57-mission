from django.utils.timezone import datetime,make_aware, now

from ..models import Period
from ..models.system_config import SystemConfig
from ..utils.cache import cached
from .config import get_config

LATEST_PERIOD_KEY = "period.latest"

@cached(key=LATEST_PERIOD_KEY, ttl=60 * 60 * 24)
def get_latest_period() -> Period | None:
    return Period.objects.order_by('-year', '-month').first()

PERIODS_KEY = "period.all"
@cached(key=PERIODS_KEY, ttl=60 * 60 * 24)
def get_all_periods() -> list[Period]:
    return list(Period.objects.order_by('-year', '-month').all())

def get_report_deadline(period: Period | None = None):
    cutoff_lock_disabled = get_config(SystemConfig.Key.QUOTA_LOCK_AFTER_DEADLINE)=="false"
    if cutoff_lock_disabled:
        return None
    period = period or get_latest_period()
    cutoff_day = int(get_config(SystemConfig.Key.QUOTA_CUTOFF_DAY))
    cutoff_time = datetime.strptime(get_config(SystemConfig.Key.QUOTA_CUTOFF_TIME), '%H:%M').time()
    cutoff_datetime = make_aware(
        datetime(
            year=period.year,
            month=period.month + (1 if cutoff_day > now().day else 0),
            day=cutoff_day,
            hour=cutoff_time.hour,
            minute=cutoff_time.minute,
            second=cutoff_time.second,
        )
    )
    return cutoff_datetime

def get_department_report_deadline(period: Period | None = None):
    cutoff_lock_disabled = get_config(SystemConfig.Key.REPORT_REMIND_BEFORE_DAYS)=="false"
    if cutoff_lock_disabled:
        return None
    period = period or get_latest_period()
    cutoff_day = int(get_config(SystemConfig.Key.REPORT_CUTOFF_DAY))
    cutoff_time = datetime.strptime(get_config(SystemConfig.Key.REPORT_CUTOFF_TIME), '%H:%M').time()
    cutoff_datetime = make_aware(
        datetime(
            year=period.year,
            month=period.month,
            day=cutoff_day,
            hour=cutoff_time.hour,
            minute=cutoff_time.minute,
            second=cutoff_time.second,
        )
    )
    return cutoff_datetime
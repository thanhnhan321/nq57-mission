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

def get_quota_report_deadline(period: Period | None = None):
    cutoff_lock_disabled = get_config(SystemConfig.Key.QUOTA_LOCK_AFTER_DEADLINE)=="false"
    if cutoff_lock_disabled:
        return None
    cutoff_day = int(get_config(SystemConfig.Key.QUOTA_CUTOFF_DAY))
    cutoff_time = datetime.strptime(get_config(SystemConfig.Key.QUOTA_CUTOFF_TIME), '%H:%M').time()
    # nếu có thông tin kỳ -> ngày chốt của kỳ đó là trong tháng sau
    if period:
        month = 1 + period.month
    # nếu không có thông tin kỳ -> tìm ngày chốt kỳ gần nhất
    else:
        period = get_latest_period()
        month = period.month + (0 if cutoff_day > now().day else 1)
    cutoff_datetime = make_aware(
        datetime(
            year=period.year,
            month=month,
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

def get_mission_deadline(period: Period | None = None):
    cutoff_lock_disabled = get_config(SystemConfig.Key.MISSION_REMIND_BEFORE_DAYS)=="false"
    if cutoff_lock_disabled:
        return None
    period = period or get_latest_period()
    cutoff_day = int(get_config(SystemConfig.Key.MISSION_CUTOFF_DAY))
    cutoff_time = datetime.strptime(get_config(SystemConfig.Key.MISSION_CUTOFF_TIME), '%H:%M').time()
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


def get_mission_cutoff_day() -> int:
    raw = get_config(SystemConfig.Key.MISSION_CUTOFF_DAY)
    try:
        cutoff_day = int(raw)
    except (TypeError, ValueError):
        cutoff_day = 10

    if cutoff_day < 1:
        return 1
    if cutoff_day > 28:
        return 28
    return cutoff_day
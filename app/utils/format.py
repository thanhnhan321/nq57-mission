from datetime import datetime, date
from django.utils import timezone

from .. import constants

def format_number(value: float | int | None):
    try:
        if value is None:
            return "—"
        if isinstance(value, int):
            return f"{value:,}".replace(',', ' ')
        return f"{float(value):,.2f}".replace(',', ' ')
    except (ValueError, TypeError):
        return "—"

def format_text(value):
    try:
        if value is None:
            return "—"
        return str(value)
    except (ValueError, TypeError):
        return "—"

def format_date(value: datetime | date | None):
    try:
        if value is None:
            return "—"
        if isinstance(value, datetime):
            return timezone.localtime(value).strftime(constants.DATE_FORMAT)
        return value.strftime(constants.DATE_FORMAT)
    except (ValueError, TypeError):
        return "—"

def format_datetime(value: datetime | None):
    try:
        if value is None:
            return "—"
        return timezone.localtime(value).strftime(constants.DATETIME_FORMAT)
    except (ValueError, TypeError):
        return "—"
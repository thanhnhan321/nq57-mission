from django.urls import path

from .list import ReportPeriodMonthListView, ReportPeriodMonthListPartialView
from .update import ReportPeriodMonthUpdateView

urlpatterns = [
    path(
        "",
        ReportPeriodMonthListView.as_view(),
        name="report_period_month_list",
    ),
    path(
        "partial/",
        ReportPeriodMonthListPartialView.as_view(),
        name="report_period_month_list_partial",
    ),
    path(
        "update/",
        ReportPeriodMonthUpdateView.as_view(),
        name="report_period_month_update",
    ),
]
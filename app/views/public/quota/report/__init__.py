
from django.urls import path

from .list import PublicQuotaReportListView, PublicQuotaReportListPartialView
from .summary import PublicQuotaReportSummaryView, PublicQuotaReportSummaryPartialView

urlpatterns = [
    path("", PublicQuotaReportListView.as_view(), name="public_quota_report_list"),
    path("partial/", PublicQuotaReportListPartialView.as_view(), name="public_quota_report_list_partial"),
    path("summary/", PublicQuotaReportSummaryView.as_view(), name="public_quota_report_summary"),
    path("summary/partial/", PublicQuotaReportSummaryPartialView.as_view(), name="public_quota_report_summary_partial"),
]
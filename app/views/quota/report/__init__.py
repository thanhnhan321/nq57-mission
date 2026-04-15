
from django.urls import path

from .list import QuotaReportListView, QuotaReportListPartialView
from .summary import QuotaReportSummaryView, QuotaReportSummaryPartialView
from .update import QuotaReportUpdateView
from .bulk_update import QuotaReportBulkUpdateView

urlpatterns = [
    path('', QuotaReportListView.as_view(), name='quota_report_list'),
    path('partial/', QuotaReportListPartialView.as_view(), name='quota_report_list_partial'),
    path('summary/', QuotaReportSummaryView.as_view(), name='quota_report_summary'),
    path('summary/partial/', QuotaReportSummaryPartialView.as_view(), name='quota_report_summary_partial'),
    path('update/', QuotaReportUpdateView.as_view(), name='quota_report_update'),
    path('bulk-update/', QuotaReportBulkUpdateView.as_view(), name='quota_report_bulk_update'),
]
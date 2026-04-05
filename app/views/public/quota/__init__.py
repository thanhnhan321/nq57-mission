from django.urls import path, include

from .list import PublicQuotaListView, PublicQuotaListPartialView
from .detail import PublicQuotaDetailView
from .summary import PublicQuotaSummaryView
from . import report

urlpatterns = [
    path("", PublicQuotaListView.as_view(), name="public_quota_list"),
    path("partial/", PublicQuotaListPartialView.as_view(), name="public_quota_list_partial"),
    path("detail/", PublicQuotaDetailView.as_view(), name="public_quota_detail"),
    path("summary/", PublicQuotaSummaryView.as_view(), name="public_quota_summary"),
    path("reports/", include(report)),
]
from django.urls import path, include
from .list import MissionReportListView, MissionReportListPartialView
from .detail import PublicMissionDetailView
# from .summary import PublicQuotaSummaryView
from .options import public_mission_result_report_period_filter_options

urlpatterns = [
    path("", MissionReportListView.as_view(), name="public_mission_list"),
    path("partial/", MissionReportListPartialView.as_view(), name="public_mission_list_partial"),
    path("detail/", PublicMissionDetailView.as_view(), name="public_mission_detail"),
    path(
        "<str:pk>/report-period-options/",
        public_mission_result_report_period_filter_options,
        name="public_mission_result_report_period_filter_options",
    ),
]
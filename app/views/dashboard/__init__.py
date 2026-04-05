from django.urls import path

from .dashboard import DashboardPageView
from .dashboard import DashboardPanelView
from .department_performance import DepartmentPerformanceListView, DepartmentPerformancePartialView
from .mission import MissionPanelPartialView

urlpatterns = [
    path("", DashboardPageView.as_view(), name="dashboard"),
    path("panel/", DashboardPanelView.as_view(), name="dashboard_panel"),
    path("department_performance/", DepartmentPerformanceListView.as_view(), name="department_performance"),
    path("department_performance_partial/", DepartmentPerformancePartialView.as_view(), name="department_performance_partial"),
    path("mission_panel/", MissionPanelPartialView.as_view(), name="mission_panel_partial"),
]

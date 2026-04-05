
from django.urls import path

from .dashboard import PublicDashboardPageView, PublicDashboardPanelView

urlpatterns = [
    path("", PublicDashboardPageView.as_view(), name="public_dashboard"),
    path("panel/", PublicDashboardPanelView.as_view(), name="public_dashboard_panel"),
]
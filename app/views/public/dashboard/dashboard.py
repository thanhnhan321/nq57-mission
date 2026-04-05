from django.views.generic.base import TemplateView

from .quota import PublicQuotaDashboardView
from .mission import PublicMissionDashboardView

class PublicDashboardPageView(TemplateView):
    template_name = "public/dashboard/dashboard.html"

class PublicDashboardPanelView(TemplateView):
    def get(self, request, *args, **kwargs):
        panel = request.GET.get('panel', 'mission')
        if panel == 'quota':
            return PublicQuotaDashboardView.as_view()(request, *args, **kwargs)
        else:
            return PublicMissionDashboardView.as_view()(request, *args, **kwargs)
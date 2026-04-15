from django.views.generic.base import TemplateView

from ....handlers.period import get_latest_period
from .quota import PublicQuotaDashboardView
from .mission import PublicMissionDashboardView

class PublicDashboardPageView(TemplateView):
    template_name = "public/dashboard/dashboard.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        latest_year = get_latest_period().year
        context['year'] = latest_year
        return context

class PublicDashboardPanelView(TemplateView):
    def get(self, request, *args, **kwargs):
        panel = request.GET.get('panel', 'mission')
        if panel == 'quota':
            return PublicQuotaDashboardView.as_view()(request, *args, **kwargs)
        else:
            return PublicMissionDashboardView.as_view()(request, *args, **kwargs)
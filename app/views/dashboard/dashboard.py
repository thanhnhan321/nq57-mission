from django.contrib.auth.views import login_required, method_decorator
from django.urls import reverse
from django.views.generic.base import TemplateView

from ...handlers.period import get_latest_period
from .quota import QuotaPanelView
from .mission import MissionPanelView 

@method_decorator(login_required, name="dispatch")
class DashboardPageView(TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        latest_period = get_latest_period()
        context['latest_year'] = latest_period.year
        context['breadcrumbs'] = f'<a href="{reverse("dashboard")}" class="hover:underline">Tổng quan</a>'
        return context

@method_decorator(login_required, name="dispatch")
class DashboardPanelView(TemplateView):
    def get(self, request, *args, **kwargs):
        panel = request.GET.get('panel', '').strip()
        if panel == 'quota':
            return QuotaPanelView.as_view()(request, *args, **kwargs)
        return MissionPanelView.as_view()(request, *args, **kwargs)
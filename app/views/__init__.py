from django.urls import include, path
from django.views.generic import RedirectView

from . import (
    dashboard,
    ui_showcase,
    profile,
    system,
    mission,
    categories,
    directive_document,
    options,
    report,
    quota,
    document,
    public,
)
from .auth import SignInView, sign_out

urlpatterns = [
    path('', RedirectView.as_view(url='public/'), name='root'),
    path('sign-in/', SignInView.as_view(), name='login'),
    path('sign-out/', sign_out, name='logout'),
    path('dashboard/', include(dashboard)),
    path('profile/', include(profile)),
    path('ui-showcase/', include(ui_showcase)),
    path('mission/', include(mission)),
    path('categories/', include(categories)),
    path('directive-documents/', include(directive_document)),
    path('system/', include(system)),
    path('options/', include(options)),
    path('report/', include(report)),
    path('quotas/', include(quota)),
    path('document/', include(document)),
    path('public/', include(public)),
]
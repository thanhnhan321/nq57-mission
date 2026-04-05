
from django.urls import include, path
from django.views.generic import RedirectView

from . import dashboard
from . import quota
from . import document
from . import mission

urlpatterns = [
    path('', RedirectView.as_view(url='dashboard/'), name='public_root'),
    path('dashboard/', include(dashboard)),
    path('quotas/', include(quota)),
    path('documents/', include(document)),
    path('missions/', include(mission)),
]
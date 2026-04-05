from django.urls import path

from .views.page import ConfigurationPageView
from .views.partial import ConfigurationPartialView


urlpatterns = [
    path('configurations', ConfigurationPageView.as_view(), name='configuration_list'),
    path('configurations/partial', ConfigurationPartialView.as_view(), name='configuration_partial'),
]
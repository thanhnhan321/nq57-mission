
from django.urls import path

from .list import DirectiveLevelListView, DirectiveLevelListPartialView
from .create import DirectiveLevelCreateView
from .delete import DirectiveLevelDeleteView
from .update import DirectiveLevelUpdateView

urlpatterns = [
    path('', DirectiveLevelListView.as_view(), name='directive_level_list'),
    path('partial/', DirectiveLevelListPartialView.as_view(), name='directive_level_list_partial'),
    path('create/', DirectiveLevelCreateView.as_view(), name='directive_level_create'),
    path('update/', DirectiveLevelUpdateView.as_view(), name='directive_level_update'),
    path('delete/', DirectiveLevelDeleteView.as_view(), name='directive_level_delete'),
]
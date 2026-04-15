
from django.urls import path

from .list import RankingListView, RankingListPartialView
from .update import RankingUpdateView


urlpatterns = [
    path('', RankingListView.as_view(), name='ranking_list'),
    path('partial/', RankingListPartialView.as_view(), name='ranking_list_partial'),
    path('update/', RankingUpdateView.as_view(), name='ranking_update'),
]
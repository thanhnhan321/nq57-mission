from django.urls import include, path

from . import rank

urlpatterns = [
    path('ranks/', include(rank)),
]
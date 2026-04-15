from django.urls import path

from .views.create import DepartmentCreateView
from .views.page import DepartmentListView
from .views.update import DepartmentUpdateView
from .views.partial import DepartmentListPartialView


urlpatterns = [
    path('departments', DepartmentListView.as_view(), name='department_list'),
    path('departments/partial', DepartmentListPartialView.as_view(), name='department_list_partial'),
    path('departments/create', DepartmentCreateView.as_view(), name='department_create'),
    path('departments/update', DepartmentUpdateView.as_view(), name='department_update'),
]
from django.urls import path

from .export import UserExportView
from .views.active_status_options import UserActiveStatusOptionsView
from .views.create import UserCreateView
from .views.page import UserManagementPageView
from .views.partial import UserManagementPartialView
from .views.role_options import UserRoleOptionsView
from .views.update import UserUpdateView


urlpatterns = [
    path('users', UserManagementPageView.as_view(), name='user_list'),
    path('users/partial', UserManagementPartialView.as_view(), name='user_list_partial'),
    path('users/create', UserCreateView.as_view(), name='user_create'),
    path('users/update', UserUpdateView.as_view(), name='user_update'),
    path('users/export', UserExportView.as_view(), name='user_export'),
    path('users/active-status-options', UserActiveStatusOptionsView.as_view(), name='user_active_status_options'),
    path('users/role-options', UserRoleOptionsView.as_view(), name='user_role_options'),
]

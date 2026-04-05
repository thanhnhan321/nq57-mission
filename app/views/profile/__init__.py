from django.urls import path
from .profile import ChangePasswordApiView, ProfileApiView, ProfilePageView

urlpatterns = [
    path('', ProfilePageView.as_view(), name='profile'),
    path('api/', ProfileApiView.as_view(), name='profile_api'),
    path('change-password/', ChangePasswordApiView.as_view(), name='profile_change_password'),
]
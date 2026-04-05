from app.views.system.departments import urlpatterns as department_urlpatterns
from app.views.system.configurations import urlpatterns as configuration_urlpatterns
from app.views.system.users import urlpatterns as user_urlpatterns

urlpatterns = user_urlpatterns + department_urlpatterns + configuration_urlpatterns
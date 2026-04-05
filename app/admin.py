from django.contrib import admin

# Register your models here.
from .models import __all__

for model in __all__:
    admin.site.register(model)
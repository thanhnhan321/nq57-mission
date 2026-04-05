from django.urls import include, path

from . import directive_level, document_type, report_type

urlpatterns = [
    path('directive-levels/', include(directive_level)),
    path('document-types/', include(document_type)),
    path('report-types/', include(report_type)),
    # path('reports/', include(report)),
]
from django.urls import path

from .document_type import document_type_options
from .directive_level import directive_level_options
from .department import (
    department_report_department_options,
    department_type_options,
    department_report_status_options,
    department_report_type_options,
    department_options,
    department_status_options,
)
from .quota import quota_report_status_options, quota_evaluation_result_options, quota_type_options
from .document import (
    document_number_options,
    document_name_options,
    document_status_options,
)
from .period import period_options, year_options
from .mission import mission_name_options

urlpatterns = [
    path('document-types/', document_type_options, name='document_type_options'),
    path('directive-levels/', directive_level_options, name='directive_level_options'),
    path('report-departments/', department_report_department_options, name='department_report_department_options'),
    path('department-types/', department_type_options, name='department_type_options'),
    path('department-status-options/', department_status_options, name='department_status_options'),
    path('report-status/', department_report_status_options, name='department_report_status_options'),
    path('report-types/', department_report_type_options, name='department_report_type_options'),
    path('departments/', department_options, name='department_options'),
    path('quota-report-statuses/', quota_report_status_options, name='quota_report_status_options'),
    path('quota-evaluation-results/', quota_evaluation_result_options, name='quota_evaluation_result_options'),
    path('quota-types/', quota_type_options, name='quota_type_options'),
    path('document-number/', document_number_options, name='document_number_options'),
    path('document-name/', document_name_options, name='document_name_options'),
    path('document-status/', document_status_options, name='document_status_options'),
    path('periods/', period_options, name='period_options'),
    path('years/', year_options, name='year_options'),
    path('mission-name/', mission_name_options, name='mission_name_options'),
]
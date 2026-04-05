from django.urls import path
# from .views import (
#     DepartmentReportListPageView,
#     DepartmentReportListPartialView,
# )
from .list import(
DepartmentReportListView,
DepartmentReportListPartialView
)
from .export_excel import (
    export_detail_report_excel,
    export_summary_report_excel,
)
from .create import (
    create_report_modal,
    department_report_create_department_options,
    department_report_period_options,
    department_report_upload_temp,
    department_report_submit,
)

from .update import DepartmentReportUpdateView
from .download import DepartmentReportDownloadView
from .run_task import department_report_run_task_api

urlpatterns = [
    path("", DepartmentReportListView.as_view(), name="department_report_list"),
    path("partial/", DepartmentReportListPartialView.as_view(), name="department_report_list_partial"),

    path("create/modal/", create_report_modal, name="department_report_create_modal"),
    path(
        "create/options/departments/",
        department_report_create_department_options,
        name="department_report_create_department_options",
    ),
    path("options/report-periods/", department_report_period_options, name="department_report_period_options"),

    path("export/detail/", export_detail_report_excel, name="export_detail_report_excel"),
    path("export/summary/", export_summary_report_excel, name="export_summary_report_excel"),
    path("upload-temp/", department_report_upload_temp, name="department_report_upload_temp"),
    path("submit/", department_report_submit, name="department_report_submit"),
    path('department-report/<int:pk>/update/', DepartmentReportUpdateView.as_view(), name='department_report_update',),
    path("download/", DepartmentReportDownloadView.as_view(), name="department_report_download"),
    path("run-task/", department_report_run_task_api, name="department_report_run_task_api"),
]

from django.urls import include, path

from .import report
from .list import QuotaListView, QuotaListPartialView
from .create import QuotaCreateView
from .import_ import QuotaImportView
from .update import QuotaUpdateView
from .delete import QuotaDeleteView
from .detail import QuotaDetailView
from .summary import QuotaSummaryView
from .export_summary_quota import export_quota_excel
from .export_summary_department import ExportSummaryDepartmentView

urlpatterns = [
    path('', QuotaListView.as_view(), name='quota_list'),
    path('partial/', QuotaListPartialView.as_view(), name='quota_list_partial'),
    path('create/', QuotaCreateView.as_view(), name='quota_create'),
    path('import/', QuotaImportView.as_view(), name='quota_import'),
    path('update/', QuotaUpdateView.as_view(), name='quota_update'),
    path('delete/', QuotaDeleteView.as_view(), name='quota_delete'),
    path('detail/', QuotaDetailView.as_view(), name='quota_detail'),
    path('summary/', QuotaSummaryView.as_view(), name='quota_summary'),
    path('reports/', include(report)),
    path('export-excel/', export_quota_excel, name='summary_quota_export_excel'),
    path('export-summary-department-excel/', ExportSummaryDepartmentView.as_view(), name='summary_department_export_excel'),
]
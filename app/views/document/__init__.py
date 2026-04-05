from django.urls import path

from .list import DocumentListView, DocumentListPartialView
from .create import DocumentCreateView
from .update import DocumentUpdateView
from .delete import DocumentDeleteView, DocumentDeleteConfirmView
from .download import DocumentDownloadView
from .export import DocumentExportView

urlpatterns = [
    path("", DocumentListView.as_view(), name="document_list"),
    path("partial/", DocumentListPartialView.as_view(), name="document_list_partial"),
    path("create/", DocumentCreateView.as_view(), name="document_create"),
    path("update/", DocumentUpdateView.as_view(), name="document_update"),
    path("delete/confirm/", DocumentDeleteConfirmView.as_view(), name="document_delete_confirm"),
    path("delete/", DocumentDeleteView.as_view(), name="document_delete"),
    path("download/", DocumentDownloadView.as_view(), name="document_download"),
    path("export/", DocumentExportView.as_view(), name="document_export"),
]
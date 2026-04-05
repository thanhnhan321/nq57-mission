from django.urls import path

from .list import PublicDocumentListView, PublicDocumentListPartialView
from .download import PublicDocumentDownloadView

urlpatterns = [
    path("", PublicDocumentListView.as_view(), name="public_document_list"),
    path("partial/", PublicDocumentListPartialView.as_view(), name="public_document_list_partial"),
    path("download/", PublicDocumentDownloadView.as_view(), name="public_document_download"),
]
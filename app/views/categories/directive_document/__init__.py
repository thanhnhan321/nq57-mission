
from django.urls import path

from .list import DirectiveDocumentListView, DirectiveDocumentListPartialView
from .create import DirectiveDocumentCreateView
from .update import DirectiveDocumentUpdateView
from .delete import DirectiveDocumentDeleteView
from .download import DirectiveDocumentDownloadView

urlpatterns = [
    path('', DirectiveDocumentListView.as_view(), name='directive_document_list'),
    path('partial/', DirectiveDocumentListPartialView.as_view(), name='directive_document_list_partial'),
    path('create/', DirectiveDocumentCreateView.as_view(), name='directive_document_create'),
    path('update/', DirectiveDocumentUpdateView.as_view(), name='directive_document_update'),
    path('delete/', DirectiveDocumentDeleteView.as_view(), name='directive_document_delete'),
    path('download/', DirectiveDocumentDownloadView.as_view(), name='directive_document_download'),
]
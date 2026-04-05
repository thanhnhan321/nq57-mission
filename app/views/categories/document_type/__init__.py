
from django.urls import path

from .list import DocumentTypeListView, DocumentTypeListPartialView
from .create import DocumentTypeCreateView
from .delete import DocumentTypeDeleteView
from .update import DocumentTypeUpdateView


urlpatterns = [
    path('', DocumentTypeListView.as_view(), name='document_type_list'),
    path('partial/', DocumentTypeListPartialView.as_view(), name='document_type_list_partial'),
    path('create/', DocumentTypeCreateView.as_view(), name='document_type_create'),
    path('update/', DocumentTypeUpdateView.as_view(), name='document_type_update'),
    path('delete/', DocumentTypeDeleteView.as_view(), name='document_type_delete'),
]
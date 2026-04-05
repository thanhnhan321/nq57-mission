from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import method_decorator
from django.db.models import Q, Exists, OuterRef
from django.urls import reverse
from django.views.generic import ListView

from ....models.document import DocumentType, DirectiveDocument
from ...templates.components.button import Button
from ...templates.components.table import TableContext, TableAction, TableRowAction, FilterParam, TableColumn

COLUMNS = [
    TableColumn(
        name='code',
        label='Mã',
        sortable=True,
    ),
    TableColumn(
        name='name',
        label='Tên',
        sortable=True,
    ) 
]

FILTERS = [
    FilterParam(
        name='search',
        label='Từ khóa',
        placeholder='Tìm kiếm theo mã, tên',
        type=FilterParam.Type.TEXT,
        query=lambda value: Q(code__icontains=value) | Q(name__icontains=value),
    ),
]

def table_actions(request):
    if not request.user.is_superuser:
        return []
    return  [
        TableAction(
            label='Thêm',
            icon='plus.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.FILLED,
            disabled=False,
            extra_attributes={
                '@click': f'''$dispatch("modal:open", {{
                    url: "{reverse("document_type_create")}",
                    title: "Thêm mới loại văn bản",
                    ariaLabel: "Thêm mới loại văn bản",
                    closeEvent: "document-type:success",
                }});'''
            }
        ),
    ]

def row_actions(request):
    if not request.user.is_superuser:
        return []
    return [
        TableRowAction(
            icon='edit.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.OUTLINED,
            disabled=False,
            key='code',
            extra_attributes={
                '@click': f'''$dispatch("modal:open", {{
                    url: "{reverse("document_type_update", query={"code": "__ROW_ID__"})}",
                    title: "Cập nhật loại văn bản",
                    ariaLabel: "Cập nhật loại văn bản",
                    closeEvent: "document-type:success",
                }});'''
            }
        ),
        TableRowAction(
            icon='trash.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.FILLED,
            disabled=False,
            render_predicate=lambda row: not row['cannot_delete'],
            htmx_event_prefix='document-type',
            key='code',
            extra_attributes={
                'hx-get': f'{reverse("document_type_delete", query={"code": "__ROW_ID__"})}',
                'hx-swap': 'none',
                'hx-confirm': 'Bạn có chắc chắn muốn xóa loại văn bản này không? Dữ liệu sẽ không thể khôi phục lại sau khi xóa.',
            }
        )
    ]

def get_common_context(request):
    base_query = (
        DocumentType.objects
        .annotate(
            cannot_delete=Exists(DirectiveDocument.objects.filter(type_id=OuterRef('pk')))
        )
        .values('code', 'name', 'cannot_delete')
    )
    table_context = TableContext(
        request=request,
        reload_event='document-type:success',
        columns=COLUMNS,
        filters=FILTERS,
        partial_url=reverse('document_type_list_partial'),
        actions=table_actions(request),
        row_actions=row_actions(request),
    )
    return {
        **table_context.to_response_context(base_query),
    }

@method_decorator(permission_required('app.view_documenttype'), name='dispatch')
class DocumentTypeListView(ListView):
    model = DocumentType
    template_name = "categories/document_type/list.html"

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

class DocumentTypeListPartialView(DocumentTypeListView):
    template_name = "categories/document_type/partial.html"
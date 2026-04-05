from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import method_decorator
from django.db.models import Q, Exists, OuterRef
from django.urls import reverse
from django.views.generic import ListView

from ...models import DirectiveDocument, Mission
from ..templates.components.button import Button
from ..templates.components.table import TableContext, TableAction, TableRowAction, FilterParam, TableColumn

COLUMNS = [
    TableColumn(
        name='code',
        label='Mã',
        sortable=True,
    ),
    TableColumn(
        name='title',
        label='Tên văn bản chỉ đạo',
        sortable=True,
    ),
    TableColumn(
        name='type__name',
        label='Loại',
        sortable=True,
    ),
    TableColumn(
        name='directive_level__name',
        label='Cấp chỉ đạo',
        sortable=True,
    ),
    TableColumn(
        name='issued_at',
        label='Ngày ban hành',
        sortable=True,
        type=TableColumn.Type.DATE,
    ),
    TableColumn(
        name='valid_from',
        label='Ngày bắt đầu hiệu lực',
        sortable=True,
        type=TableColumn.Type.DATE,
    ),
    TableColumn(
        name='valid_to',
        label='Ngày kết thúc hiệu lực',
        sortable=True,
        type=TableColumn.Type.DATE,
    )
]

def table_filters():
    return [
        FilterParam(
            name='search',
            label='Từ khóa',
            placeholder='Tìm kiếm theo tên',
            type=FilterParam.Type.TEXT,
            query=lambda value: Q(title__icontains=value),
        ),
        FilterParam(
            name='type',
            label='Loại',
            type=FilterParam.Type.SELECT,
            query=lambda value: Q(type_id=value),
            placeholder='Chọn loại văn bản',
            extra_attributes={
                'options_url': reverse('document_type_options'),
            },
        ),
        FilterParam(
            name='level',
            label='Cấp chỉ đạo',
            type=FilterParam.Type.SELECT,
            query=lambda value: Q(directive_level_id=value),
            placeholder='Chọn cấp chỉ đạo',
            extra_attributes={
                'options_url': reverse('directive_level_options'),
            },
        ),
        FilterParam(
            name='valid_from',
            label='Bắt đầu hiệu lực từ',
            type=FilterParam.Type.DATE,
            query=lambda value: Q(valid_from__gte=value),
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
                    url: "{reverse("directive_document_create")}",
                    title: "Thêm mới văn bản chỉ đạo",
                    ariaLabel: "Thêm mới văn bản chỉ đạo",
                    closeEvent: "directive-document:success",
                }});'''
            }
        ),
    ]

def row_actions(request):
    actions = [
        TableRowAction(
            icon='download.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.FILLED,
            disabled=False,
            key='code',
            href=reverse('directive_document_download', query={'code': '__ROW_ID__'}),
            extra_attributes={
                'download': '__object__file_name__',
            }
        ),
    ]
    if request.user.is_superuser:
        actions.extend([
            TableRowAction(
                icon='edit.svg',
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.OUTLINED,
                disabled=False,
                key='code',
                extra_attributes={
                    '@click': f'''$dispatch("modal:open", {{
                        url: "{reverse("directive_document_update", query={"code": "__ROW_ID__"})}",
                        title: "Cập nhật văn bản chỉ đạo",
                        ariaLabel: "Cập nhật văn bản chỉ đạo",
                        closeEvent: "directive-document:success",
                    }});'''
                }
            ),
            TableRowAction(
                icon='trash.svg',
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.FILLED,
                disabled=False,
                render_predicate=lambda row: not row['cannot_delete'],
                htmx_event_prefix='directive-document',
                key='code',
                extra_attributes={
                    'hx-get': f'{reverse("directive_document_delete", query={"code": "__ROW_ID__"})}',
                    'hx-swap': 'none',
                    'hx-confirm': 'Bạn có chắc chắn muốn xóa văn bản chỉ đạo này không? Dữ liệu sẽ không thể khôi phục lại sau khi xóa.',
                }
            )
        ])
    return actions

def get_common_context(request):
    base_query = (
        DirectiveDocument.objects
        .select_related('type', 'directive_level', 'object')
        .annotate(
            cannot_delete=Exists(Mission.objects.filter(directive_document_id=OuterRef('code')))
        )
        .values(
            'code',
            'title',
            'type__name',
            'directive_level__name',
            'issued_at',
            'valid_from',
            'valid_to',
            'object__file_name',
            'cannot_delete',
        )
    )
    table_context = TableContext(
        request=request,
        reload_event='directive-document:success',
        columns=COLUMNS,
        filters=table_filters(),
        partial_url=reverse('directive_document_list_partial'),
        actions=table_actions(request),
        row_actions=row_actions(request),
    )
    return {
        **table_context.to_response_context(base_query),
    }

@method_decorator(permission_required('app.view_directivedocument'), name='dispatch')
class DirectiveDocumentListView(ListView):
    model = DirectiveDocument
    template_name = "directive_document/list.html"

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

class DirectiveDocumentListPartialView(DirectiveDocumentListView):
    template_name = "directive_document/partial.html"
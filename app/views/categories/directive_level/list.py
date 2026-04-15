from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import method_decorator
from django.db.models import Q, Exists, OuterRef
from django.urls import reverse
from django.views.generic import ListView

from ....models.document import DirectiveLevel, DirectiveDocument
from ...templates.components.button import Button
from ...templates.components.table import TableContext, TableAction, TableRowAction, FilterParam, TableColumn

COLUMNS = [
    TableColumn(
        name='name',
        label='Mã',
        sortable=True,
    ),
    TableColumn(
        name='description',
        label='Tên',
        sortable=True,
    ),
]

def table_filters():
        return [
        FilterParam(
            name='search',
            label='Từ khóa',
            placeholder='Tìm kiếm theo mã, tên',
            type=FilterParam.Type.TEXT,
            query=lambda value: Q(name__icontains=value) | Q(description__icontains=value),
        ),
    ]

def table_actions(request):
    if not request.user.is_superuser:
        return []
    return [
        TableAction(
            label='Thêm mới',
            icon='plus.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.FILLED,
            disabled=False,
            extra_attributes={
                '@click': f'''$dispatch("modal:open", {{
                    url: "{reverse("directive_level_create")}",
                    title: "Thêm mới cấp chỉ đạo",
                    ariaLabel: "Thêm mới cấp chỉ đạo",
                    closeEvent: "directive-level:success",
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
            extra_attributes={
                '@click': f'''$dispatch("modal:open", {{
                    url: "{reverse("directive_level_update", query={"id": "__ROW_ID__"})}",
                    title: "Cập nhật cấp chỉ đạo",
                    ariaLabel: "Cập nhật cấp chỉ đạo",
                    closeEvent: "directive-level:success",
                }});''',
                'title': 'Chỉnh sửa',
            }
        ),
        TableRowAction(
            icon='trash.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.FILLED,
            disabled=False,
            render_predicate=lambda row: not row['cannot_delete'],
            htmx_event_prefix='directive-level',
            extra_attributes={
                'hx-get': f'{reverse("directive_level_delete", query={"id": "__ROW_ID__"})}',
                'hx-swap': 'none',
                'hx-confirm': 'Bạn có chắc chắn muốn xóa cấp chỉ đạo này không? Dữ liệu sẽ không thể khôi phục lại sau khi xóa.',
                'title': 'Xóa',
            }
        )
    ]

def get_common_context(request):
    base_query = (
        DirectiveLevel.objects
        .annotate(
            cannot_delete=Exists(DirectiveDocument.objects.filter(directive_level=OuterRef('pk')))
        )
        .values('id', 'name', 'description', 'cannot_delete')
    )
    table_context = TableContext(
        request=request,
        reload_event='directive-level:success',
        columns=COLUMNS,
        filters=table_filters(),
        partial_url=reverse('directive_level_list_partial'),
        actions=table_actions(request),
        row_actions=row_actions(request),
    )
    return {
        **table_context.to_response_context(base_query),
    }

@method_decorator(permission_required('app.view_directivelevel'), name='dispatch')
class DirectiveLevelListPartialView(ListView):
    model = DirectiveLevel
    template_name = "categories/directive_level/partial.html"

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

@method_decorator(permission_required('app.view_directivelevel'), name='dispatch')
class DirectiveLevelListView(DirectiveLevelListPartialView):
    template_name = "categories/directive_level/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = f'Danh mục / <a href="{reverse("directive_level_list")}" class="hover:underline">Cấp chỉ đạo</a>'
        return context


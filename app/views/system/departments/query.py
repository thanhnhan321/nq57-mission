from dataclasses import dataclass
from typing import Any, Callable

from django.urls import reverse

from ....models import Department
from ....constants import OPTION_COLOR_CLASS_MAP
from ..utils.text import normalize_text
from ..utils.tree import build_tree, filter_tree, iter_tree
from ...options.department import department_status_label
from ...templates.components.button import Button
from ...templates.components.table import FilterParam, TableAction, TableRowAction


PAGE_TITLE = 'Danh sách đơn vị'
EMPTY_MESSAGE = 'Không có đơn vị phù hợp.'
SORTABLE_COLUMNS = {'stt', 'short_name'}


@dataclass(frozen=True)
class DepartmentTableColumn:
    name: str
    label: str
    width: str | None = None
    sortable: bool = False
    formatter: Callable[[Any], Any] | None = None
    is_hypertext: bool = False
    need_tooltip: bool = False
    align: str = 'center'

    def format(self, value: Any):
        return self.formatter(value) if self.formatter else value


def _center_value(value):
    return value or '—'


def _center_formatter(value):
    return f'<div class="flex justify-center w-full">{_center_value(value)}</div>'


def _get_type_label(department):
    return f'<div class="flex justify-center w-full">{department.get_type_display()}</div>'


def _get_status_label(value):
    color = 'green' if value else 'red'
    badge = f'<div class="w-fit rounded-full {OPTION_COLOR_CLASS_MAP[color]} text-xs px-2 py-1">{department_status_label(value)}</div>'
    return f'<div class="flex justify-center w-full">{badge}</div>'


COLUMNS = [
    DepartmentTableColumn(name='stt', label='STT', width='72px', sortable=True),
    DepartmentTableColumn(name='short_name', label='Mã đơn vị', width='140px', formatter=_center_formatter, sortable=True),
    DepartmentTableColumn(name='name', label='Tên đơn vị', width='45%', formatter=lambda value: value, align='left'),
    DepartmentTableColumn(name='is_active', label='Trạng thái', width='120px', formatter=_get_status_label),
    DepartmentTableColumn(name='type', label='Loại đơn vị', width='140px', formatter=_get_type_label),
]


def table_filters():
    return [
        FilterParam(
            name='search',
            label='Từ khóa',
            placeholder='Tìm kiếm theo mã, tên, đơn vị cha',
            type=FilterParam.Type.TEXT,
            query=lambda value: value,
        ),
        FilterParam(
            name='type',
            label='Loại đơn vị',
            placeholder='Tất cả',
            type=FilterParam.Type.SELECT,
            extra_attributes={'options_url': '/app/options/department-types/'},
            query=lambda value: value,
        ),
        FilterParam(
            name='is_active',
            label='Trạng thái',
            placeholder='Tất cả',
            type=FilterParam.Type.SELECT,
            extra_attributes={'options_url': '/app/options/department-status-options/'},
            query=lambda value: value,
        ),
    ]


def _matches_department(department, search_query):
    if not search_query:
        return True

    normalized_query = search_query.casefold()
    values = [
        department.short_name or '',
        department.name or '',
        department.get_short_label(),
        department.get_type_display(),
    ]
    parent = getattr(department, 'parent', None)
    if parent:
        values.extend([
            parent.short_name or '',
            parent.name or '',
            parent.get_short_label(),
        ])

    return any(normalized_query in value.casefold() for value in values if value)


def _matches_department_filters(department, search_query, type_value, is_active_value):
    if type_value and department.type != type_value:
        return False
    if is_active_value == 'active' and not department.is_active:
        return False
    if is_active_value == 'inactive' and department.is_active:
        return False
    return _matches_department(department, search_query)


def _normalize_sort_field(sort_field):
    return sort_field if sort_field in SORTABLE_COLUMNS else ''


def _normalize_sort_direction(sort_direction):
    return 'desc' if (sort_direction or '').strip().lower() == 'desc' else 'asc'


def _department_sort_key(node, sort_field):
    department = node.item
    if sort_field == 'short_name':
        return (
            (department.short_name or '').casefold(),
            (department.name or '').casefold(),
            department.id,
        )
    return department.id


def _sort_department_tree(nodes, sort_field, sort_direction):
    if not sort_field:
        return list(nodes)

    reverse = sort_direction == 'desc'
    sorted_nodes = sorted(nodes, key=lambda node: _department_sort_key(node, sort_field), reverse=reverse)
    for node in sorted_nodes:
        node.children = _sort_department_tree(node.children, sort_field, sort_direction)
    return sorted_nodes


def _tree_row(node, depth, ancestor_ids):
    department = node.item
    return {
        'id': department.id,
        'stt': 0,
        'short_name': department.short_name,
        'name': department.name,
        'is_active': department.is_active,
        'type': department,
        'depth': depth,
        'has_children': bool(node.children),
        'ancestor_ids': ancestor_ids,
    }


def _parse_positive_int(value, default):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _decorate_tree_search_text(node):
    child_texts = [_decorate_tree_search_text(child) for child in node.children]
    values = [node.item.name or '']
    short_name = getattr(node.item, 'short_name', '') or ''
    if short_name:
        values.append(short_name)
    values.extend(child_texts)
    node.search_text = normalize_text(' '.join(values))
    return node.search_text


def _build_department_tree(request):
    search_query = request.GET.get('search', '').strip()
    type_value = request.GET.get('type', '').strip()
    is_active_value = request.GET.get('is_active', '').strip()
    sort = _normalize_sort_field(request.GET.get('sort', '').strip())
    sort_direction = _normalize_sort_direction(request.GET.get('sort_direction', 'asc'))
    page_index = _parse_positive_int(request.GET.get('page_index', '0'), 0)
    page_size = _parse_positive_int(request.GET.get('page_size', '10'), 10)

    queryset = Department.objects.select_related('parent').order_by('id')
    tree_nodes = build_tree(list(queryset))
    if search_query or type_value or is_active_value:
        tree_nodes = filter_tree(
            tree_nodes,
            lambda department: _matches_department_filters(department, search_query, type_value, is_active_value),
        )

    tree_nodes = _sort_department_tree(tree_nodes, sort, sort_direction)

    total_count = len(tree_nodes)
    total_pages = max((total_count + page_size - 1) // page_size, 1)
    page_index = min(page_index, total_pages - 1)
    page_start = page_index * page_size
    page_end = page_start + page_size
    page_tree_nodes = tree_nodes[page_start:page_end]

    rows = []
    for index, (node, depth, ancestor_ids) in enumerate(iter_tree(page_tree_nodes), start=1):
        node.display_index = index
        row = _tree_row(node, depth, ancestor_ids)
        row['stt'] = index
        rows.append(row)
    tree_expanded_ids = [row['id'] for row in rows if row['has_children']]

    return {
        'search_query': search_query,
        'type_value': type_value,
        'is_active_value': is_active_value,
        'page_index': page_index,
        'page_size': page_size,
        'total_count': total_count,
        'tree_nodes': page_tree_nodes,
        'rows': rows,
        'tree_expanded_ids': tree_expanded_ids,
        'sort': sort,
        'sort_direction': sort_direction,
    }


def table_actions():
    return [
        TableAction(
            label='Thêm mới',
            icon='plus.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.FILLED,
            disabled=False,
            extra_attributes={
                '@click': f'''$dispatch("modal:open", {{
                    url: "{reverse('department_create')}",
                    title: "Thêm mới đơn vị",
                    ariaLabel: "Thêm mới đơn vị",
                    closeEvent: "department:success",
                }});'''
            },
        ),
    ]


def row_actions():
    return [
        TableRowAction(
            label='',
            icon='edit.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.OUTLINED,
            disabled=False,
            extra_attributes={
                '@click': (
                    'window.dispatchEvent(new CustomEvent("modal:open", { detail: { url: "'
                    + reverse('department_update', query={'id': '__ROW_ID__'})
                    + '", title: "Cập nhật đơn vị", ariaLabel: "Cập nhật đơn vị", closeEvent: "department:success" } }))'
                ),
                'title': 'Cập nhật đơn vị',
                'aria-label': 'Cập nhật đơn vị',
            },
        ),
    ]


def get_department_tree_context(request):
    data = _build_department_tree(request)
    filter_values = {
        'search': data['search_query'],
        'type': data['type_value'],
        'is_active': data['is_active_value'],
    }
    return {
        'page_title': PAGE_TITLE,
        'partial_url': reverse('department_list_partial'),
        'filters': [
            filter_param.copy(update={'value': filter_values.get(filter_param.name, '')})
            for filter_param in table_filters()
        ],
        'columns': COLUMNS,
        'rows': data['rows'],
        'page_index': data['page_index'],
        'page_size': data['page_size'],
        'total_count': data['total_count'],
        'tree_mode': True,
        'tree_expanded_ids': data['tree_expanded_ids'],
        'search_query': data['search_query'],
        'type_value': data['type_value'],
        'is_active_value': data['is_active_value'],
        'type_options': Department.Type.choices,
        'tree_nodes': data['tree_nodes'],
        'empty_message': EMPTY_MESSAGE,
        'sort': data['sort'],
        'sort_direction': data['sort_direction'],
        'reload_event': 'department:success',
        'actions': table_actions(),
        'row_actions': row_actions(),
    }


def _decorate_department_tree_search_text(node):
    return _decorate_tree_search_text(node)


def get_department_create_context(request=None):
    tree_nodes = build_tree(list(Department.objects.select_related('parent').order_by('id')))
    for node in tree_nodes:
        _decorate_department_tree_search_text(node)
    return {
        'parent_tree_nodes': tree_nodes,
        'parent_tree_selected_id': '',
        'parent_tree_placeholder': 'Chọn đơn vị cha',
        'parent_tree_empty_message': 'Không có đơn vị nào',
    }

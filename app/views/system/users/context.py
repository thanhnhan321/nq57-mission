from ..utils.text import normalize_text
from ..utils.tree import build_tree
from ....models import Department


def _decorate_department_tree_search_text(node):
    child_texts = [_decorate_department_tree_search_text(child) for child in node.children]
    values = [node.item.name or '']
    short_name = getattr(node.item, 'short_name', '') or ''
    if short_name:
        values.append(short_name)
    values.extend(child_texts)
    node.search_text = normalize_text(' '.join(values))
    return node.search_text


def build_department_tree_context():
    tree_nodes = build_tree(list(Department.objects.select_related('parent').order_by('id')))
    for node in tree_nodes:
        _decorate_department_tree_search_text(node)

    return {
        'department_tree_nodes': tree_nodes,
        'department_tree_placeholder': 'Chọn đơn vị',
        'department_tree_empty_message': 'Không có đơn vị nào',
    }

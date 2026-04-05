from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, TypeVar


T = TypeVar('T')


@dataclass(slots=True)
class TreeNode:
    item: Any
    children: list['TreeNode'] = field(default_factory=list)
    search_text: str = ''
    display_index: int | None = None


def _get_value(item: Any, attribute_name: str) -> Any:
    if isinstance(item, dict):
        return item.get(attribute_name)
    return getattr(item, attribute_name)


def build_tree(
    items: Iterable[T],
    *,
    id_attr: str = 'id',
    parent_attr: str = 'parent_id',
) -> list[TreeNode]:
    roots: list[TreeNode] = []
    nodes_by_id: dict[Any, TreeNode] = {}
    pending_children: dict[Any, list[TreeNode]] = {}

    for item in items:
        node = TreeNode(item=item)
        item_id = _get_value(item, id_attr)
        parent_id = _get_value(item, parent_attr)
        nodes_by_id[item_id] = node

        if item_id in pending_children:
            node.children.extend(pending_children.pop(item_id))

        if parent_id is None:
            roots.append(node)
            continue

        parent = nodes_by_id.get(parent_id)
        if parent is None:
            pending_children.setdefault(parent_id, []).append(node)
            continue

        parent.children.append(node)

    return roots


def filter_tree(nodes: Iterable[TreeNode], predicate: Callable[[Any], bool]) -> list[TreeNode]:
    filtered_nodes: list[TreeNode] = []

    for node in nodes:
        filtered_children = filter_tree(node.children, predicate)
        if predicate(node.item) or filtered_children:
            filtered_nodes.append(TreeNode(item=node.item, children=filtered_children))

    return filtered_nodes


def _get_node_id(node: TreeNode) -> Any:
    return node.item.get('id') if isinstance(node.item, dict) else getattr(node.item, 'id', None)


def iter_tree(nodes: Iterable[TreeNode], depth: int = 0, ancestor_ids: list[Any] | None = None):
    ancestors = list(ancestor_ids or [])
    for node in nodes:
        yield node, depth, ancestors
        yield from iter_tree(node.children, depth + 1, [*ancestors, _get_node_id(node)])

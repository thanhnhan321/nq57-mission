from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import method_decorator
from django.db.models import Q
from django.urls import reverse
from django.views.generic import ListView

from ....models.rank import Ranking
from ...templates.components.button import Button
from ...templates.components.table import (
    TableContext, TableAction, TableRowAction, FilterParam, TableColumn
)
from ....handlers.leader import render_rank_badge
# ===================== COLUMNS =====================
COLUMNS = [
    TableColumn(name='code', label='Xếp loại', sortable=False),
    TableColumn(name='name', label='Tên xếp loại', sortable=False),
    TableColumn(name='score_from', label='Điểm từ', sortable=False),
    TableColumn(name='score_to', label='Điểm đến', sortable=False),
    TableColumn(name='description', label='Mô tả'),
]

# ===================== FILTER =====================
def table_filters():
    return [
        FilterParam(
            name='search',
            label='Từ khóa',
            placeholder='Tìm theo mã, tên...',
            type=FilterParam.Type.TEXT,
            query=lambda value: Q(code__icontains=value) | Q(name__icontains=value),
        ),
    ]


# ===================== ROW ACTION =====================
def row_actions(request):
    if not request.user.is_superuser:
        return []

    return [
        TableRowAction(
            icon='edit.svg',
            variant=Button.Variant.OUTLINED,
            key='id',
            extra_attributes={
                '@click': f'''$dispatch("modal:open", {{
                    url: "{reverse("ranking_update", query={"id": "__ROW_ID__"})}",
                    title: "Cập nhật xếp loại",
                    closeEvent: "ranking:success",
                }});''',
                'title': 'Chỉnh sửa',
            }
        ),
    ]

# ===================== CONTEXT =====================
def get_common_context(request):
    base_query = (
        Ranking.objects
        .filter(is_active=True)
        .values(
            'id',
            'code',
            'name',
            'score_from',
            'score_to',
            'description'
        )
        .order_by('code')
    )

    rows = []
    for row in base_query:
        row['code'] = render_rank_badge(row['code'])
        rows.append(row)

    table_context = TableContext(
        request=request,
        reload_event='ranking:success',
        columns=COLUMNS,
        filters=[],
        partial_url=reverse('ranking_list_partial'),
        actions=[],
        row_actions=row_actions(request),
        show_ordinal=True,
    )

    return {
        **table_context.to_response_context(rows),
    }

# ===================== VIEW =====================
@method_decorator(permission_required('app.view_ranking'), name='dispatch')
class RankingListPartialView(ListView):
    model = Ranking
    template_name = "leader/rank/partial.html"

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)


@method_decorator(permission_required('app.view_ranking'), name='dispatch')
class RankingListView(RankingListPartialView):
    template_name = "leader/rank/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = f'Danh mục / <a href="{reverse("ranking_list")}" class="hover:underline">Xếp loại</a>'
        return context
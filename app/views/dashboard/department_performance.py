from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import method_decorator
from django.db.models import (
    F,
    Q,
    Case,
    Count,
    FloatField,
    Value,
    When,
)
from django.urls import reverse
from django.views.generic import ListView

from ...models import QuotaReport, Department
from ..templates.components.table import TableContext,  TableColumn

COLUMNS = [
    TableColumn(
        name='name',
        label='Đơn vị',
        align='left',
    ),
    TableColumn(
        name='submitted_count',
        label='Số báo cáo đã gửi',
        type=TableColumn.Type.NUMBER,
        sortable=True,
        align='right',
    ),
    TableColumn(
        name='total_count',
        label='Số báo cáo yêu cầu',
        type=TableColumn.Type.NUMBER,
        sortable=True,
        align='right',
    ),
    TableColumn(
        name='submission_rate',
        label='Tỉ lệ báo cáo',
        type=TableColumn.Type.TEXT,
        formatter=lambda value: f'<span class="font-bold text-{'red' if value < 0.5 else 'green' if value > 0.8 else 'yellow'}-500">{value*100:.2f}%</span>',
        sortable=True,
        align='right',
    ),
]


def get_common_context(request):
    year = request.GET.get('year', '').strip()
    department_id = request.GET.get('department_id', '').strip()
    queryset = Department.objects
    agg_filter = Q()
    filter = Q()
    if year.isdigit():
        agg_filter &= Q(quota_reports__period__year=year)
    if department_id.isdigit():
        agg_filter &= Q(quota_reports__department_id=department_id)
        filter &= Q(id=department_id)

    queryset = (
        queryset.filter(filter)
        .annotate(
            submitted_count=Count(
                'quota_reports',
                filter=~Q(quota_reports__status__in=[QuotaReport.Status.NOT_SENT, QuotaReport.Status.REJECTED]) & agg_filter
            ),
            total_count=Count('quota_reports', filter=agg_filter)
        )
        .filter(total_count__gt=0)
        .annotate(
            submission_rate=F('submitted_count') * 1.0 / F('total_count')
        )
        .order_by('submission_rate', 'total_count', 'submitted_count')
        .values('name', 'submitted_count', 'total_count', 'submission_rate')
    )
    table_context = TableContext(
        request=request,
        columns=COLUMNS,
        partial_url=reverse('department_performance_partial', query={"year": year, "department_id": department_id}),
    )

    return {
        **table_context.to_response_context(queryset)
    }

@method_decorator(permission_required('app.view_department'), name='dispatch')
class DepartmentPerformanceListView(ListView):
    model = Department
    template_name = "dashboard/department_performance.html"

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

class DepartmentPerformancePartialView(DepartmentPerformanceListView):
    template_name = "dashboard/department_performance_partial.html"
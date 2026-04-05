from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from app.models import Mission
from app.models.mission import MissionReport


@require_GET
def public_mission_result_report_period_filter_options(request, pk):
    mission = get_object_or_404(
        Mission.objects.filter(is_active=True),
        pk=pk,
    )

    report_pairs = (
        MissionReport.objects
        .filter(mission_id=mission.pk)
        .values_list("report_year", "report_month")
        .distinct()
        .order_by("-report_year", "-report_month")
    )

    data = [{"value": "all", "label": "Tất cả tháng"}]
    data.extend(
        {
            "value": f"{int(year)}-{int(month):02d}",
            "label": f"Tháng {int(month):02d}/{int(year)}",
        }
        for year, month in report_pairs
    )

    return JsonResponse(data, safe=False)
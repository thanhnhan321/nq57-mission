from django.http import JsonResponse

from ...models import Period
from ...handlers.period import get_all_periods

def period_options(request):
    def convert_to_options(periods: list[Period]) -> list[dict]:
        return [
            {
                "value": period.id,
                "label": f"Tháng {period.month:02d}/{period.year}"
            }
            for period in periods
        ]
    quota_id = request.GET.get('quota_id', '').strip()
    if not quota_id.isdigit():
        data = convert_to_options(get_all_periods())
    else:
        data = convert_to_options(Period.objects.filter(quota_reports__quota_id=quota_id))
    return JsonResponse(data, safe=False)

def year_options(request):
    def convert_to_options(years: list[int]) -> list[dict]:
        return [
            {
                "value": year,
                "label": f"{year}"
            }
            for year in years
        ]
    data = convert_to_options(Period.objects.values_list('year', flat=True).distinct().order_by('-year'))
    return JsonResponse(data, safe=False)
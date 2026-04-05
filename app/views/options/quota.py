from django.http import JsonResponse

from ...constants import OPTION_COLOR_CLASS_MAP
from ...models import Quota,QuotaReport

def quota_report_status_options(request):
    data = [
        {
            "value": status,
            "label": label,
            "klass": OPTION_COLOR_CLASS_MAP[QuotaReport.Status(status).color],
        }
        for status, label in QuotaReport.Status.choices
    ]
    return JsonResponse(data, safe=False)

def quota_evaluation_result_options(request):
    data = [
        {
            "value": True,
            "label": "Đạt",
            "klass": OPTION_COLOR_CLASS_MAP["green"],
        },
        {
            "value": False,
            "label": "Không đạt",
            "klass": OPTION_COLOR_CLASS_MAP["red"],
        },
    ]
    return JsonResponse(data, safe=False)

def quota_type_options(request):
    data = [
        {
            "value": type,
            "label": label,
        }
        for type, label in Quota.Type.choices
    ]
    return JsonResponse(data, safe=False)
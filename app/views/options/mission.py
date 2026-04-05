from django.http import JsonResponse

from ...models import Mission

from django.http import JsonResponse

def mission_name_options(request):
    missions = (
        Mission.objects
        .exclude(code__isnull=True)
        .exclude(code__exact="")
        .exclude(name__isnull=True)
        .exclude(name__exact="")
        .values("code", "name")
        .distinct()
        .order_by("name", "code")
    )

    data = [
        {"value": item["code"], "label": item["name"]}
        for item in missions
    ]
    return JsonResponse(data, safe=False)

from django.http import JsonResponse

from ...handlers.directive_level import get_all_directive_levels

def directive_level_options(request):
    data = get_all_directive_levels()
    return JsonResponse([{"value": item.id, "label": item.name} for item in data], safe=False)
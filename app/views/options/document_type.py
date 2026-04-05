from django.http import JsonResponse

from ...models import DocumentType

def document_type_options(request):
    data = [
        {"value": item["code"], "label": item["name"]}
        for item in DocumentType.objects.values("code", "name")
    ]
    return JsonResponse(data, safe=False)
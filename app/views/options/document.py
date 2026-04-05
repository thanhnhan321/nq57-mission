from django.http import JsonResponse

from ...models import Document

def document_number_options(request):
    data = [
        {"value": item["code"], "label": item["code"]}
        for item in Document.objects.values("code", "code")
    ]
    return JsonResponse(data, safe=False)

def document_name_options(request):
    data = [
        {"value": item["title"], "label": item["title"]}
        for item in Document.objects.values("title").distinct()
    ]
    return JsonResponse(data, safe=False)


def document_status_options(request):
    """
    Options for the document list "Tình trạng" filter.
    Matches values used by app/views/document/list.py:
    - active
    - expired
    """
    data = [
        {"value": "active", "label": "Hiệu lực"},
        {"value": "expired", "label": "Hết hiệu lực"},
    ]
    return JsonResponse(data, safe=False)


# Backwards-compatible alias (older routes referenced this name)
document_number = document_number_options
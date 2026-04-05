import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def dropzone_upload_demo(request: HttpRequest) -> HttpResponse:
    """
    Showcase endpoint for `components/input/file/dropzone.html`.

    It returns a simple "file card" HTML snippet and includes a hidden input
    whose name matches the uploaded field key, and whose value stores the
    generated object id.
    """
    if request.method != "POST":
        return HttpResponse(status=405)

    cards: list[dict] = []
    if not request.FILES:
        return HttpResponse("")

    for field_name, files in request.FILES.lists():
        for f in files:
            size_bytes = getattr(f, "size", 0) or 0
            size_kb = round(size_bytes / 1024, 1) if size_bytes else 0
            cards.append(
                {
                    "field_name": field_name,
                    "object_id": uuid.uuid4().hex,
                    "file_name": getattr(f, "name", "file") or "file",
                    "size_kb": size_kb,
                }
            )

    return render(request, "ui_showcase/dropzone_file_cards.html", {"cards": cards})


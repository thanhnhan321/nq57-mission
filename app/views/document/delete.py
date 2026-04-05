from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from ...models import Document


@method_decorator(permission_required("app.delete_document"), name="dispatch")
class DocumentDeleteConfirmView(View):
    template_name = "document/delete.html"

    def get(self, request, *args, **kwargs):
        code = request.GET.get("code", "").strip()

        if not code:
            return HttpResponse("Thiếu mã văn bản", status=HTTPStatus.UNPROCESSABLE_ENTITY)

        document = Document.objects.filter(code=code).first()
        if not document:
            return HttpResponse("Văn bản không tồn tại", status=HTTPStatus.UNPROCESSABLE_ENTITY)

        return render(
            request,
            self.template_name,
            {
                "code": document.code,
                "title": document.title,
            },
        )


@method_decorator(permission_required("app.delete_document"), name="dispatch")
class DocumentDeleteView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code", "").strip()

        if not code:
            messages.warning(request, "Chưa chọn văn bản")
            return JsonResponse(
                {"message": "Chưa chọn văn bản"},
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        try:
            document = Document.objects.filter(code=code).first()

            if not document:
                messages.warning(request, "Văn bản không tồn tại")
                return JsonResponse(
                    {"message": "Văn bản không tồn tại"},
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                )

            document.delete()
            messages.success(request, "Xóa văn bản thành công")

            response = JsonResponse(
                {"message": "Xóa thành công"},
                status=HTTPStatus.OK,
            )
            response["HX-Trigger"] = "document:success"
            return response

        except Exception as e:
            messages.error(request, str(e))
            return JsonResponse(
                {"message": str(e)},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
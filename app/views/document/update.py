from http import HTTPStatus
from datetime import date

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import permission_required

from ...models import Document, DocumentType, Period, Department


@method_decorator(permission_required("app.change_document"), name="dispatch")
class DocumentUpdateView(View):
    template_name = "document/update.html"

    @staticmethod
    def _normalize_department_value(value):
        if value in (None, "", []):
            return ""
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    def get_context_data(
        self,
        code="",
        title="",
        type_code="",
        issued_at="",
        issued_by="",
        expired_at="",
        errors=None,
    ):
        return {
            "code": code,
            "title": title,
            "type_code": type_code,
            "issued_at": issued_at,
            "issued_by": self._normalize_department_value(issued_by),
            "expired_at": expired_at,
            "errors": errors or {},
        }

    def get(self, request, *args, **kwargs):
        code = request.GET.get("code", "").strip()
        if not code:
            messages.warning(request, "Chưa chọn văn bản")
            response = HttpResponse()
            response["HX-Redirect"] = reverse("document_list")
            return response

        document = Document.objects.filter(code=code).select_related("type").first()
        if not document:
            messages.warning(request, "Văn bản không tồn tại")
            response = HttpResponse()
            response["HX-Redirect"] = reverse("document_list")
            return response

        department = Department.objects.filter(name=document.issued_by).first()
        issued_by_id = department.id if department else ""

        return render(
            request,
            self.template_name,
            self.get_context_data(
                code=document.code,
                title=document.title,
                type_code=document.type_id,
                issued_at=document.issued_at,
                issued_by=issued_by_id,
                expired_at=document.expired_at,
                errors={},
            ),
        )

    def post(self, request, *args, **kwargs):
        errors = {}

        code = request.POST.get("code", "").strip()
        title = request.POST.get("title", "").strip()
        type_code = request.POST.get("type_code", "").strip()
        issued_at = request.POST.get("issued_at", "").strip()
        issued_by_id_raw = request.POST.get("issued_by", "").strip()
        expired_at = request.POST.get("expired_at", "").strip()

        issued_by_value = self._normalize_department_value(issued_by_id_raw)

        if not code:
            errors["code"] = "Chưa chọn văn bản"

        if not title:
            errors["title"] = "Tên văn bản / trích yếu là bắt buộc"

        if not type_code:
            errors["type_code"] = "Loại văn bản là bắt buộc"

        if not issued_at:
            errors["issued_at"] = "Ngày ban hành là bắt buộc"

        if not issued_by_id_raw:
            errors["issued_by"] = "Đơn vị ban hành là bắt buộc"

        if errors:
            return render(
                request,
                self.template_name,
                self.get_context_data(
                    code=code,
                    title=title,
                    type_code=type_code,
                    issued_at=issued_at,
                    issued_by=issued_by_value,
                    expired_at=expired_at,
                    errors=errors,
                ),
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        try:
            document = Document.objects.filter(code=code).first()
            if not document:
                errors["code"] = "Văn bản không tồn tại"

            document_type = DocumentType.objects.filter(code=type_code).first()
            if not document_type:
                errors["type_code"] = "Loại văn bản không tồn tại"

            department = Department.objects.filter(id=issued_by_value).first()
            if not department:
                errors["issued_by"] = "Đơn vị ban hành không tồn tại"

            issued_at_value = None
            expired_at_value = None

            try:
                issued_at_value = date.fromisoformat(issued_at)
            except ValueError:
                errors["issued_at"] = "Ngày ban hành không hợp lệ"

            if expired_at:
                try:
                    expired_at_value = date.fromisoformat(expired_at)
                except ValueError:
                    errors["expired_at"] = "Ngày hết hiệu lực không hợp lệ"

            if issued_at_value and expired_at_value and expired_at_value < issued_at_value:
                errors["expired_at"] = "Ngày hết hiệu lực không được nhỏ hơn ngày ban hành"

            if errors:
                return render(
                    request,
                    self.template_name,
                    self.get_context_data(
                        code=code,
                        title=title,
                        type_code=type_code,
                        issued_at=issued_at,
                        issued_by=issued_by_value,
                        expired_at=expired_at,
                        errors=errors,
                    ),
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                )

            with transaction.atomic():
                period, _ = Period.objects.get_or_create(
                    year=issued_at_value.year,
                    month=issued_at_value.month,
                )

                document.title = title
                document.type = document_type
                document.issued_at = issued_at_value
                document.issued_by = department.name
                document.expired_at = expired_at_value
                document.period = period
                if not document.created_by:
                    document.created_by = request.user.username
                document.save()

            messages.success(request, "Cập nhật văn bản thành công")

            response = render(
                request,
                self.template_name,
                self.get_context_data(
                    code=document.code,
                    title=document.title,
                    type_code=document.type_id,
                    issued_at=document.issued_at,
                    issued_by=department.id,
                    expired_at=document.expired_at,
                    errors={},
                ),
            )
            response["HX-Trigger-After-Swap"] = "document:success"
            return response

        except Exception as e:
            messages.error(request, str(e))
            return render(
                request,
                self.template_name,
                self.get_context_data(
                    code=code,
                    title=title,
                    type_code=type_code,
                    issued_at=issued_at,
                    issued_by=issued_by_value,
                    expired_at=expired_at,
                    errors=errors,
                ),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
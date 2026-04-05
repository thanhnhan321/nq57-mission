from http import HTTPStatus
from datetime import date

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import permission_required

from ...models import Document, DocumentType, Storage, Period, Department
from utils import minio


@method_decorator(permission_required("app.add_document"), name="dispatch")
class DocumentCreateView(View):
    template_name = "document/create.html"

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
        return render(
            request,
            self.template_name,
            self.get_context_data(),
        )

    def post(self, request, *args, **kwargs):
        errors = {}
        status = HTTPStatus.OK

        code = request.POST.get("code", "").strip()
        title = request.POST.get("title", "").strip()
        type_code = request.POST.get("type_code", "").strip()
        issued_at = request.POST.get("issued_at", "").strip()
        expired_at = request.POST.get("expired_at", "").strip()
        issued_by_id_raw = request.POST.get("issued_by", "").strip()
        issued_by_value = self._normalize_department_value(issued_by_id_raw)
        issued_by_name = ""
        object_file = request.FILES.get("object")

        if not issued_by_id_raw:
            errors["issued_by"] = "Đơn vị ban hành là bắt buộc"
        else:
            dept = Department.objects.filter(id=issued_by_value).first()
            if not dept:
                errors["issued_by"] = "Đơn vị không tồn tại"
            else:
                issued_by_name = dept.name

        if not code:
            errors["code"] = "Số hiệu văn bản là bắt buộc"

        if not title:
            errors["title"] = "Tên văn bản / trích yếu là bắt buộc"

        if not type_code:
            errors["type_code"] = "Loại văn bản là bắt buộc"

        if not issued_at:
            errors["issued_at"] = "Ngày ban hành là bắt buộc"

        if not object_file:
            errors["object"] = "Vui lòng tải lên file đính kèm"

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

            today = date.today()
            if issued_at_value and (
                issued_at_value.year > today.year
                or (issued_at_value.year == today.year and issued_at_value.month > today.month)
            ):
                errors["issued_at"] = "Ngày ban hành không được lớn hơn tháng hiện tại"

            document_type = DocumentType.objects.filter(code=type_code).first()
            if not document_type:
                errors["type_code"] = "Loại văn bản không tồn tại"

            if Document.objects.filter(code=code).exists():
                errors["code"] = "Số hiệu văn bản đã tồn tại"

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

                storage = Storage(
                    file_name=object_file.name,
                    size=object_file.size,
                )
                storage.save(user=request.user)
                minio.upload(object_file, storage.object_uid)

                document = Document(
                    code=code,
                    title=title,
                    type=document_type,
                    issued_at=issued_at_value,
                    issued_by=issued_by_name,
                    expired_at=expired_at_value,
                    object=storage,
                    period=period,
                    created_by=request.user.username,
                    updated_by=request.user.username,
                )
                document.save()

            messages.success(request, "Thêm văn bản thành công")

            response = render(
                request,
                self.template_name,
                self.get_context_data(),
            )
            response["HX-Trigger-After-Swap"] = "document:success"
            return response

        except Exception as e:
            messages.error(request, str(e))
            status = HTTPStatus.INTERNAL_SERVER_ERROR

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
            status=status,
        )
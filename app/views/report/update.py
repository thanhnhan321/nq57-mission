import json
import os
import re
from http import HTTPStatus

from django.db import transaction
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required

from app.models.department_report import DepartmentReport
from app.models.storage import Storage
from utils import minio

from .create import _build_report_filename, _resolve_department_code

_VERSION_SUFFIX_RE = re.compile(r"_v(\d+)\.pdf$", re.IGNORECASE)


def _next_versioned_pdf_name(current_stored_name: str, base_pdf_name: str) -> str:
    stem, ext = os.path.splitext((base_pdf_name or "").strip())
    if ext.lower() != ".pdf":
        ext = ".pdf"

    name = (current_stored_name or "").strip()
    next_n = 2

    m = _VERSION_SUFFIX_RE.search(name)
    if m:
        next_n = int(m.group(1)) + 1

    return f"{stem}_v{next_n}{ext}"


class DepartmentReportUpdateView(View):
    template_name = "report/update.html"

    def get_report(self, pk):
        return get_object_or_404(
            DepartmentReport.objects.select_related("file", "department"),
            pk=pk,
        )

    def get_context(self, report, errors=None):
        old_storage = getattr(report, "file", None)

        old_file_url = "#"
        if old_storage and hasattr(old_storage, "get_presigned_url"):
            try:
                old_file_url = old_storage.get_presigned_url()
            except Exception:
                old_file_url = "#"

        return {
            "report": report,
            "update_url": reverse("department_report_update", kwargs={"pk": report.pk}),
            "old_file_name": getattr(old_storage, "file_name", "") if old_storage else "",
            "old_file_url": old_file_url,
            "last_updated_at": (
                timezone.localtime(report.updated_at).strftime("%d/%m/%Y %H:%M")
                if getattr(report, "updated_at", None)
                else ""
            ),
            "errors": errors or {},
        }

    def get(self, request, pk, *args, **kwargs):
        report = self.get_report(pk)
        return render(request, self.template_name, self.get_context(report))

    def post(self, request, pk, *args, **kwargs):
        report = self.get_report(pk)
        old_storage = getattr(report, "file", None)
        errors = {}

        upload_file = request.FILES.get("file")
        if not upload_file:
            errors["file"] = "Vui lòng tải lên file PDF"
        elif not upload_file.name.lower().endswith(".pdf"):
            errors["file"] = "Chỉ chấp nhận file PDF"
        elif upload_file.size > 20 * 1024 * 1024:
            errors["file"] = "Dung lượng file tối đa 20MB"

        if errors:
            return render(
                request,
                self.template_name,
                self.get_context(report, errors=errors),
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        try:
            with transaction.atomic():
                month = report.month if report.month is not None else 1
                base_pdf_name = _build_report_filename(
                    department_code=_resolve_department_code(report.department),
                    report_type=report.report_type or "",
                    month=month,
                    year=int(report.report_year),
                )

                current_name = getattr(old_storage, "file_name", "") if old_storage else ""
                final_file_name = _next_versioned_pdf_name(current_name, base_pdf_name)

                new_storage = Storage(
                    file_name=final_file_name,
                    size=upload_file.size,
                )
                new_storage.save(user=request.user)
                minio.upload(upload_file, new_storage.object_uid)

                report.file = new_storage
                report.file_name = final_file_name
                report.sent_at = timezone.now()
                report.save(user=request.user)

            #chưa xử lý delete cái cũ
            # if old_storage and old_storage.object_uid != new_storage.object_uid:
            #     try:
            #         minio.delete([old_storage.object_uid])
            #     except Exception as exc:
            #         print("Không xóa được file cũ trên MinIO:", exc)
            #         messages.error(request, "Có lỗi trong quá trình xử lý")

            #     try:
            #         old_storage.delete()
            #     except Exception as exc:
            #         print("Không xóa được bản ghi storage cũ:", exc)
            #         messages.error(request, "Có lỗi trong quá trình xử lý")
            messages.success(request, "Cập nhật báo cáo thành công")

        except Exception as exc:
            errors["file"] = str(exc)
            return render(
                request,
                self.template_name,
                self.get_context(report, errors=errors),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

        response = HttpResponse("", status=HTTPStatus.OK)
        response["HX-Reswap"] = "none"
        response["HX-Trigger-After-Settle"] = json.dumps({
            "department-report:success": {
                "message": "Cập nhật báo cáo thành công"
            },
            "department-report:reload": True,
            "modal:close-top": True
        })
        return response

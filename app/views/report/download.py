from django.contrib import messages
from django.http import FileResponse, HttpResponse
from django.urls import reverse
from django.views import View
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import method_decorator

import env
from ...models import DepartmentReport
from utils import minio

@method_decorator(permission_required('app.view_departmentreport'), name='dispatch')
class DepartmentReportDownloadView(View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse()
        is_htmx = request.headers.get("HX-Request") == "true"

        if is_htmx:
            params = request.GET.urlencode()
            response["HX-Redirect"] = env.HOST_URL + request.path + ("?" + params if params else "")
            return response
        else:
            response["HX-Redirect"] = reverse("department_report_list")

        report_id = request.GET.get("id", "").strip()
        if not report_id:
            messages.warning(request, "Chưa chọn báo cáo")
            return response

        report = (
            DepartmentReport.objects
            .select_related("file")
            .filter(pk=report_id)
            .first()
        )
        if not report:
            messages.warning(request, "Báo cáo không tồn tại")
            return response

        if not report.file_id:
            messages.warning(request, "Báo cáo chưa có file")
            return response

        object_response = minio.download(report.file_id)
        if object_response.status != 200:
            messages.warning(request, "Không thể tải báo cáo")
            return response

        return FileResponse(
            object_response,
            as_attachment=True,
            filename=report.file_name or report.file.file_name,
        )
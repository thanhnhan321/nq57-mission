from http import HTTPStatus
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from ...models import Quota, QuotaAssignment, QuotaReport

@method_decorator(permission_required('app.delete_quota'), name='dispatch')
class QuotaDeleteConfirmView(View):
    template_name = "quota/delete.html"

    def get(self, request, *args, **kwargs):
        quota_id = request.GET.get('id', '').strip()
        if not quota_id:
            return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Chưa chọn chỉ tiêu'})

        quota = Quota.objects.filter(id=quota_id).first()
        if not quota:
            return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Chỉ tiêu không tồn tại'})

        return render(
            request,
            self.template_name,
            {
                "id": quota.id,
                "name": quota.name,
            },
        )

@method_decorator(permission_required('app.delete_quota'), name='dispatch')
class QuotaDeleteView(View):
    def get(self, request, *args, **kwargs):
        quota_id = request.GET.get('id', '').strip()
        if not quota_id:
            messages.warning(request, 'Chưa chọn chỉ tiêu')
            return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Chưa chọn chỉ tiêu'})
        try:
            quota = Quota.objects.filter(id=quota_id).first()
            if not quota:
                messages.warning(request, 'Chỉ tiêu không tồn tại')
                return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Chỉ tiêu không tồn tại'})
            quota_submitted_report_exists = QuotaReport.objects.filter(Q(quota=quota) & ~Q(status=QuotaReport.Status.NOT_SENT)).exists()
            if quota_submitted_report_exists:
                messages.warning(request, 'Chỉ tiêu đã có báo cáo, không thể xóa')
                return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Chỉ tiêu đã có báo cáo, không thể xóa'})
            with transaction.atomic():
                QuotaAssignment.objects.filter(quota=quota).delete()
                QuotaReport.objects.filter(quota=quota).delete()
                quota.delete()
            messages.success(request, 'Xóa chỉ tiêu thành công')
            response = JsonResponse(status=HTTPStatus.OK, data={'message': 'Xóa chỉ tiêu thành công'})
            response["HX-Trigger"] = "quota:success"
            return response
        except Exception as e:
            messages.error(request, str(e))
            return JsonResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR, data={'message': str(e)})
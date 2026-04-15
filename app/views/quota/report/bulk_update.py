from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth import PermissionDenied
from django.db import transaction
from django.db.models import F, Case, OuterRef, Subquery, Value, When
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required

from ....models import Quota, QuotaReport

@method_decorator(permission_required('app.change_quotareport'), name='dispatch')
class QuotaReportBulkUpdateView(View):
    template_name = 'quota/report/bulk_update.html'
    template_form = 'quota/report/bulk_update_form.html'

    def get(self, request, *args, **kwargs):
        action = request.GET.get('action', 'reject').strip()
        report_ids = request.GET.getlist('report_ids', [])
        response = HttpResponse()
        response['HX-Redirect'] = reverse('quota_list')
        if not report_ids:
            messages.warning(request, 'Chưa chọn báo cáo chỉ tiêu')
            return response
        quota_reports = list(
            QuotaReport.objects
            .select_related('quota')
            .select_related('period')
            .filter(
                id__in=report_ids,
                status=QuotaReport.Status.PENDING
            )
        )
        if not quota_reports:
            messages.warning(request, 'Báo cáo chỉ tiêu không tồn tại')
            return response
        is_leader = all(report.quota.department_id == request.user.profile.department_id for report in quota_reports)
        if (not request.user.is_superuser and not is_leader):
            raise PermissionDenied()
        return render(
            request,
            self.template_name,
            {
                'action': action,
                'reports': quota_reports,
                'reason': '',
                'errors': {},
            }
        )

    def post(self, request, *args, **kwargs):
        errors = {}
        status = HTTPStatus.OK
        response = HttpResponse()
        response['HX-Redirect'] = reverse('quota_list')
        action = request.POST.get('action', 'reject').strip()
        report_ids = request.POST.getlist('ids', [])
        if not report_ids:
            messages.warning(request, 'Chưa chọn báo cáo chỉ tiêu')
            return response
        quota_reports = list(QuotaReport.objects.filter(id__in=report_ids, status=QuotaReport.Status.PENDING))
        is_leader = all(report.quota.department_id == request.user.profile.department_id for report in quota_reports)
        if (not request.user.is_superuser and not is_leader):
            raise PermissionDenied()
        if any(report.version != int(request.POST.get(f'version[{report.id}]', '')) for report in quota_reports):
            messages.warning(request, 'Báo cáo chỉ tiêu có cập nhật mới, vui lòng xem lại')
            return response
        reason = ''
        if action == 'reject':
            reason = request.POST.get('reason', "").strip()
            if not reason:
                errors['reason'] = 'Lý do từ chối là bắt buộc'
        if errors:
            return render(
                request,
                self.template_name,
                {
                    'action': action,
                    'reports': quota_reports,
                    'reason': reason,
                    'errors': errors,
                },
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        try:
            self.handle_bulk_reviewing(request, { quota_report.id for quota_report in quota_reports }, rejected=action == 'reject', reason=reason)
        except PermissionDenied:
            raise
        except Exception as e:
            messages.error(request, str(e))
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        return render(
            request, 
            self.template_name,
            {
                'action': action,
                'reports': quota_reports,
                'reason': reason,
                'errors': errors,
            },
            status=status,
        )

    def handle_bulk_reviewing(self, request, report_ids, rejected=False, reason=None):
        new_status=(
            QuotaReport.Status.REJECTED 
            if rejected else 
            Case(
                When(
                    actual_value__gte=F('expected_value') * Subquery(Quota.objects.filter(id=OuterRef('quota_id')).values('target_percent')[:1]),
                    expected_value__gt=0,
                    then=Value(QuotaReport.Status.PASSED)
                ),
                default=Value(QuotaReport.Status.FAILED),
            )
        )
        with transaction.atomic():
            QuotaReport.objects.select_related('quota').filter(id__in=report_ids).update(
                status=new_status,
                reason=reason if rejected else None,
                actual_value=None if rejected else F('actual_value'),
                version=F('version') + 1,
                reviewed_at=timezone.now(),
                reviewed_by=request.user.username,
            )
            messages.success(request, f'{("Từ chối" if rejected else "Phê duyệt")} hàng loạt báo cáo chỉ tiêu thành công')

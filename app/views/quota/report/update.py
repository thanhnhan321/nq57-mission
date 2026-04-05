from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth import PermissionDenied
from django.db import transaction
from django.db.models import F, Case, Exists, OuterRef, Subquery, Value, When
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.timezone import datetime, now
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required

from ....models import QuotaAssignment, Quota, QuotaReport
from ....handlers.period import get_report_deadline

EDIT_STATUSES = [QuotaReport.Status.NOT_SENT, QuotaReport.Status.PENDING, QuotaReport.Status.REJECTED]
@method_decorator(permission_required('app.change_quotareport'), name='dispatch')
class QuotaReportUpdateView(View):
    template_name = 'quota/report/update.html'

    def get(self, request, *args, **kwargs):
        id = request.GET.get('id', '').strip()
        response = HttpResponse()
        response['HX-Redirect'] = reverse('quota_list')
        if not id.isdigit():
            messages.warning(request, 'Chưa chọn chỉ tiêu báo cáo')
            return response
        quota_report = (
            QuotaReport.objects
            .select_related('quota')
            .select_related('period')
            .filter(id=id)
            .annotate(
                is_leader=Exists(
                    QuotaAssignment.objects.filter(
                        quota=OuterRef('quota_id'),
                        department_id=request.user.profile.department_id,
                        is_leader=True
                    )
                )
            )
            .first()
        )
        if not quota_report:
            messages.warning(request, 'Báo cáo chỉ tiêu không tồn tại')
            return response
        if (
            not request.user.is_superuser and 
            not quota_report.is_leader and 
            quota_report.department_id != request.user.profile.department_id
        ):
            raise PermissionDenied()
        cutoff_datetime = get_report_deadline(quota_report.period)
        can_edit = quota_report.status in EDIT_STATUSES and (
            request.user.is_superuser or (
                (not cutoff_datetime or cutoff_datetime >= now())
                and quota_report.department_id == request.user.profile.department_id
            )
        )
        return render(
            request,
            self.template_name,
            {
                'id': quota_report.id,
                'version': quota_report.version,
                'name': quota_report.quota.name,
                'register_guide': quota_report.quota.register_guide,
                'submit_guide': quota_report.quota.submit_guide,
                'expected_value': quota_report.expected_value,
                'actual_value': quota_report.actual_value,
                'note': quota_report.note,
                'reason': quota_report.reason,
                'status': quota_report.status,
                'is_leader': quota_report.is_leader,
                'can_edit': can_edit,
                'errors': {},
            }
        )

    def post(self, request, *args, **kwargs):
        errors = {}
        status = HTTPStatus.OK
        response = HttpResponse()
        response['HX-Redirect'] = reverse('quota_list')
        id = request.POST.get('id', '').strip()
        version = request.POST.get('version', '').strip()
        if not id.isdigit() or not version.isdigit():
            messages.warning(request, 'Chưa chọn chỉ tiêu báo cáo')
            return response
        quota_report = (
            QuotaReport.objects
            .select_related('quota')
            .filter(id=id)
            .annotate(
                is_leader=Exists(
                    QuotaAssignment.objects.filter(
                        quota=OuterRef('quota_id'),
                        department_id=request.user.profile.department_id,
                        is_leader=True
                    )
                )
            )
            .first()
        )
        if not quota_report:
            messages.warning(request, 'Báo cáo chỉ tiêu không tồn tại')
            return response
        if quota_report.version != int(version):
            messages.warning(request, 'Báo cáo chỉ tiêu có cập nhật mới, vui lòng xem lại')
            return render(
                request,
                'quota/report/form.html',
                {
                    'id': id,
                    'version': quota_report.version,
                    'name': quota_report.quota.name,
                    'register_guide': quota_report.quota.register_guide,
                    'submit_guide': quota_report.quota.submit_guide,
                    'expected_value': quota_report.expected_value,
                    'actual_value': quota_report.actual_value,
                    'note': quota_report.note,
                    'status': quota_report.status,
                    'reason': quota_report.reason,
                    'is_leader': quota_report.is_leader,
                    'errors': {},
                },
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        expected_value = quota_report.expected_value
        actual_value = quota_report.actual_value
        note = quota_report.note
        reason = quota_report.reason
        action = request.POST.get('action', "").strip()
        is_submit = action == 'submit' and (request.user.is_superuser or request.user.profile.department_id == quota_report.department_id)
        is_review = action != 'submit' and (request.user.is_superuser or quota_report.is_leader)
        if is_submit:
            if quota_report.status not in EDIT_STATUSES:
                messages.error(request, 'Không có quyền thao tác')
                return response
            expected_value = request.POST.get('expected_value', "").strip()
            if not expected_value:
                errors['expected_value'] = 'Chỉ tiêu phải thực hiện là bắt buộc'
            elif not expected_value.isdigit():
                errors['expected_value'] = 'Chỉ tiêu phải thực hiện phải là số tự nhiên'
            else:
                expected_value = int(expected_value)
            actual_value = request.POST.get('actual_value', "").strip()
            if not actual_value:
                errors['actual_value'] = 'Kết quả thực hiện là bắt buộc'
            elif not actual_value.isdigit():
                errors['actual_value'] = 'Kết quả thực hiện phải là số tự nhiên'
            else:
                actual_value = int(actual_value)
            note = request.POST.get('note', "").strip()
        elif is_review:
            rejected = action == 'reject'
            reason = request.POST.get('reason', "").strip()
            if not reason and rejected:
                errors['reason'] = 'Lý do từ chối là bắt buộc'
        else:
            status = HTTPStatus.FORBIDDEN
            messages.error(request, 'Không có quyền thao tác')
        if errors:
            return render(
                request,
                'quota/report/form.html',
                {
                    'id': id,
                    'version': version,
                    'expected_value': expected_value,
                    'actual_value': actual_value,
                    'note': note,
                    'reason': reason,
                    'status': quota_report.status,
                    'register_guide': quota_report.quota.register_guide,
                    'submit_guide': quota_report.quota.submit_guide,
                    'is_leader': quota_report.is_leader,
                    'errors': errors,
                },
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        try:
            if is_submit:
                cutoff_datetime = get_report_deadline(quota_report.period)
                can_edit = quota_report.status in EDIT_STATUSES and (
                    request.user.is_superuser or (
                        (not cutoff_datetime or cutoff_datetime >= now())
                        and quota_report.department_id == request.user.profile.department_id
                    )
                )
                if not can_edit:
                    messages.warning(request, 'Không có quyền thao tác')
                    status = HTTPStatus.FORBIDDEN
                else:
                    self.handle_submitting(request, id, expected_value=expected_value, actual_value=actual_value, note=note)
            elif is_review:
                self.handle_reviewing(request, id, rejected=rejected, reason=reason)
        except PermissionDenied:
            raise
        except Exception as e:
            messages.error(request, str(e))
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        return render(
            request, 
            'quota/report/form.html',
            {
                'id': id,
                'version': quota_report.version,
                'expected_value': expected_value,
                'actual_value': actual_value,
                'note': note,
                'reason': reason,
                'status': quota_report.status,
                'register_guide': quota_report.quota.register_guide,
                'submit_guide': quota_report.quota.submit_guide,
                'is_leader': quota_report.is_leader,
                'errors': errors,
            },
            status=status,
        )

    def handle_submitting(self, request, id, **kwargs):
        expected_value = kwargs.get('expected_value')
        actual_value = kwargs.get('actual_value')
        note = kwargs.get('note')
        with transaction.atomic():
            QuotaReport.objects.filter(id=id).update(
                expected_value=expected_value,
                actual_value=actual_value,
                note=note,
                status=QuotaReport.Status.PENDING,
                version=F('version') + 1,
                submit_at=datetime.now(),
                submit_by=request.user.username,
            )
            messages.success(request, 'Báo cáo chỉ tiêu đã được gửi đi, vui lòng chờ duyệt')

    def handle_reviewing(self, request, id, **kwargs):
        rejected = kwargs.get('rejected')
        reason = kwargs.get('reason')
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
            QuotaReport.objects.select_related('quota').filter(id=id).update(
                status=new_status,
                reason=reason if rejected else None,
                actual_value=0 if rejected else F('actual_value'),
                version=F('version') + 1,
                reviewed_at=datetime.now(),
                reviewed_by=request.user.username,
            )
            if rejected:
                messages.success(request, 'Đã từ chối báo cáo chỉ tiêu')
            else:
                messages.success(request, 'Đã phê duyệt báo cáo chỉ tiêu')

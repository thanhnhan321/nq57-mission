from http import HTTPStatus

from django.contrib import messages
from django.db import transaction
from django.db.models import  Q
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import dateparse
from django.views import View
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import method_decorator

from ...models import (
    Department,
    Quota,
    QuotaAssignment,
    QuotaReport,
    Period,
)
from utils.validate import isfloat
@method_decorator(permission_required('app.change_quota'), name='dispatch')
class QuotaUpdateView(View):
    template_name = 'quota/update.html'

    def get(self, request, *args, **kwargs):
        id = request.GET.get('id', '').strip()
        response = HttpResponse()
        response['HX-Redirect'] = reverse('quota_list')
        if not id:
            messages.warning(request, 'Chưa chọn chỉ tiêu')
            return response
        quota = Quota.objects.prefetch_related('department_assignments', 'department_reports').filter(id=id).first()
        if not quota:
            messages.warning(request, 'Chỉ tiêu không tồn tại')
            return response
        lead_department_id = quota.department_id
        assigned_department_ids = [assignment.department_id for assignment in quota.department_assignments.all()]
        has_submitted_reports = quota.department_reports.filter(~Q(status=QuotaReport.Status.NOT_SENT)).exists()
        return render(
            request,
            self.template_name,
            {
                'id': quota.id,
                'name': quota.name,
                'type': quota.type,
                'register_guide': quota.register_guide,
                'submit_guide': quota.submit_guide,
                'target_percent': quota.target_percent * 100,
                'issued_at': quota.issued_at,
                'expired_at': quota.expired_at,
                'lead_department_id': lead_department_id,
                'assigned_department_ids': assigned_department_ids,
                'has_submitted_reports': has_submitted_reports,
                'errors': {},
            }
        )

    def post(self, request, *args, **kwargs):
        errors = {}
        status = HTTPStatus.OK
        response = HttpResponse()
        response['HX-Redirect'] = reverse('quota_list')
        id = request.POST.get('id', '').strip()
        if not id:
            messages.warning(request, 'Chưa chọn chỉ tiêu')
            return response
        quota = Quota.objects.prefetch_related('department_assignments', 'department_reports').filter(id=id).first()
        if not quota:
            messages.warning(request, 'Chỉ tiêu không tồn tại')
            return response
        has_submitted_reports = quota.department_reports.filter(~Q(status=QuotaReport.Status.NOT_SENT)).exists()
        name = request.POST.get('name', "").strip()
        if not name:
            errors['name'] = 'Tên chỉ tiêu là bắt buộc'
        type = request.POST.get('type', "").strip()
        if not type:
            errors['type'] = 'Cách tính là bắt buộc'
        elif type not in Quota.Type.values:
            errors['type'] = 'Cách tính không hợp lệ'
        elif has_submitted_reports and type != quota.type:
            errors['type'] = 'Cách tính không được thay đổi khi đã có báo cáo đã gửi'
        register_guide = request.POST.get('register_guide', "").strip()
        if not register_guide:
            errors['register_guide'] = 'Nội dung chỉ tiêu phải thực hiện là bắt buộc'
        submit_guide = request.POST.get('submit_guide', "").strip()
        if not submit_guide:
            errors['submit_guide'] = 'Nội dung kết quả thực hiện là bắt buộc'
        target_percent = request.POST.get('target_percent', "").strip()
        if not target_percent:
            errors['target_percent'] = 'Tỉ lệ được giao là bắt buộc'
        elif not isfloat(target_percent):
            errors['target_percent'] = 'Tỉ lệ được giao phải là số thập phân'
        else:
            target_percent = float(target_percent)
        if has_submitted_reports and target_percent != quota.target_percent * 100:
            errors['target_percent'] = 'Tỉ lệ được giao không được thay đổi khi đã có báo cáo đã gửi'
        elif target_percent > 100:
            errors['target_percent'] = 'Tỉ lệ được giao không được lớn hơn 100%'
        issued_at = request.POST.get('issued_at', "").strip()
        if not issued_at:
            errors['issued_at'] = 'Ngày ban hành là bắt buộc'
        expired_at = request.POST.get('expired_at', "").strip()
        if not expired_at:
            errors['expired_at'] = 'Ngày hết hiệu lực là bắt buộc'
        lead_department_id = request.POST.get('lead_department_id', "").strip()
        if not lead_department_id.isdigit():
            errors['lead_department_id'] = 'Đơn vị chủ trì là bắt buộc'
        else:
            lead_department_id = int(lead_department_id)
        assigned_department_ids = request.POST.getlist('assigned_department_ids')
        if not assigned_department_ids:
            errors['assigned_department_ids'] = 'Đơn vị thực hiện là bắt buộc'
        else:
            try:
                assigned_department_ids = [int(id) for id in assigned_department_ids]
            except ValueError:
                errors['assigned_department_ids'] = 'Đơn vị thực hiện không hợp lệ'
        if errors:
            return render(
                request,
                'quota/form.html',
                {
                    'id': id,
                    'name': name,
                    'type': type,
                    'register_guide': register_guide,
                    'submit_guide': submit_guide,
                    'target_percent': target_percent,
                    'issued_at': issued_at,
                    'expired_at': expired_at,
                    'lead_department_id': lead_department_id,
                    'assigned_department_ids': assigned_department_ids,
                    'has_submitted_reports': has_submitted_reports,
                    'errors': errors,
                },
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        try:
            issued_at = dateparse.parse_date(issued_at)
            if has_submitted_reports and issued_at != quota.issued_at:
                errors['issued_at'] = 'Ngày ban hành không được thay đổi khi đã có báo cáo đã gửi'
            expired_at = dateparse.parse_date(expired_at)
            if issued_at > expired_at:
                errors['expired_at'] = 'Ngày hết hiệu lực không được nhỏ hơn ngày hiệu lực'
            lead_department = Department.objects.filter(id=lead_department_id).first()
            if not lead_department:
                errors['lead_department_id'] = 'Đơn vị chủ trì không tồn tại'
            assigned_departments = Department.objects.filter(id__in=assigned_department_ids)
            if not assigned_departments:
                errors['assigned_department_ids'] = 'Có đơn vị thực hiện không tồn tại'
            if errors:
                status = HTTPStatus.UNPROCESSABLE_ENTITY
            else:
                current_assigned_department_ids = {
                    assignment.department_id
                    for assignment in quota.department_assignments.all()
                }
                with transaction.atomic():
                    target_percent = target_percent / 100
                    quota.name = name
                    quota.type = type
                    quota.register_guide = register_guide
                    quota.submit_guide = submit_guide
                    quota.target_percent = target_percent
                    quota.issued_at = issued_at
                    quota.expired_at = expired_at
                    quota.department = lead_department
                    quota.save(user=request.user)
                    QuotaAssignment.objects.filter(
                        ~Q(department__in=assigned_departments),
                        quota=quota,
                    ).delete()
                    # Get current period
                    period = Period.objects.order_by('-year', '-month').first()
                    if period:
                        QuotaReport.objects.filter(
                            ~Q(department__in=assigned_departments),
                            quota=quota,
                            period=period,
                            status=QuotaReport.Status.NOT_SENT,
                        ).delete()
                    new_assignments = [
                        QuotaAssignment(
                            quota=quota,
                            department=assigned_department,
                        ).on_behalf_of(request.user)
                        for assigned_department in assigned_departments
                        if assigned_department.id not in current_assigned_department_ids
                    ]
                    QuotaAssignment.objects.bulk_create(new_assignments)
                    if expired_at.year > period.year or (
                        expired_at.year == period.year and 
                        expired_at.month >= period.month
                    ):
                        reports = [
                            QuotaReport(
                                quota=quota,
                                period=period,
                                department=assigned_department,
                                status=QuotaReport.Status.NOT_SENT,
                            ).on_behalf_of(request.user)
                            for assigned_department in assigned_departments
                            if assigned_department.id not in current_assigned_department_ids
                        ]
                        QuotaReport.objects.bulk_create(reports)
                    messages.success(request, 'Cập nhật chỉ tiêu thành công')
        except Exception as e:
            messages.error(request, str(e))
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        return render(
            request, 
            'quota/form.html',
            {
                'id': id,
                'name': name,
                'type': type,
                'register_guide': register_guide,
                'submit_guide': submit_guide,
                'target_percent': target_percent,
                'issued_at': issued_at,
                'expired_at': expired_at,
                'lead_department_id': lead_department_id,
                'assigned_department_ids': assigned_department_ids,
                'has_submitted_reports': has_submitted_reports,
                'errors': errors,
            },
            status=status,
        )


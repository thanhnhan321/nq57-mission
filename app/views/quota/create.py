from http import HTTPStatus

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required

from ...models import (
    Department,
    Quota,
    QuotaAssignment,
    QuotaReport,
    Period,
)
from ...handlers.period import get_latest_period

@method_decorator(permission_required('app.add_quota'), name='dispatch')
class QuotaCreateView(View):
    template_name = 'quota/create.html'

    def get(self, request, *args, **kwargs):
        latest_period = get_latest_period()
        return render(
            request,
            self.template_name,
            {
                'name': '',
                'type': '',
                'register_guide': '',
                'submit_guide': '',
                'target_percent': 100,
                'issued_at': timezone.datetime(latest_period.year, latest_period.month, 1).date(),
                'expired_at': None,
                'lead_department_id': None,
                'assigned_department_ids': [],
                'has_submitted_reports': False,
                'latest_period': latest_period,
                'errors': {},
            }
        )

    def post(self, request, *args, **kwargs):
        errors = {}
        status = HTTPStatus.OK
        name = request.POST.get('name', "").strip()
        if not name:
            errors['name'] = 'Tên chỉ tiêu là bắt buộc'
        type = request.POST.get('type', "").strip()
        if not type:
            errors['type'] = 'Cách tính là bắt buộc'
        elif type not in Quota.Type.values:
            errors['type'] = 'Cách tính không hợp lệ'
        register_guide = request.POST.get('register_guide', "").strip()
        if not register_guide:
            errors['register_guide'] = 'Nội dung chỉ tiêu phải thực hiện là bắt buộc'
        submit_guide = request.POST.get('submit_guide', "").strip()
        if not submit_guide:
            errors['submit_guide'] = 'Nội dung kết quả thực hiện là bắt buộc'
        target_percent = request.POST.get('target_percent', "").strip()
        if not target_percent:
            errors['target_percent'] = 'Tỉ lệ được giao là bắt buộc'
        elif not target_percent.isdigit():
            errors['target_percent'] = 'Tỉ lệ được giao phải là số tự nhiên'
        else:
            target_percent = int(target_percent)
        if target_percent > 100:
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
                    'name': name,
                    'type': type,
                    'register_guide': register_guide,
                    'submit_guide': submit_guide,
                    'target_percent': target_percent,
                    'issued_at': issued_at,
                    'expired_at': expired_at,
                    'lead_department_id': lead_department_id,
                    'assigned_department_ids': assigned_department_ids,
                    'has_submitted_reports': False,
                    'errors': errors,
                },
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        try:
            issued_at = parse_date(issued_at)
            expired_at = parse_date(expired_at)
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
                with transaction.atomic():
                    target_percent = target_percent / 100
                    new_quota = Quota(
                        name=name,
                        type=type,
                        register_guide=register_guide,
                        submit_guide=submit_guide,
                        target_percent=target_percent,
                        issued_at=issued_at,
                        expired_at=expired_at,
                    )
                    new_quota.save(user=request.user)
                    assignments = [
                        QuotaAssignment(
                            quota=new_quota,
                            department=assigned_department,
                            is_leader=False,
                        ).on_behalf_of(request.user)
                        for assigned_department in assigned_departments
                    ]
                    assignments.append(
                        QuotaAssignment(
                            quota=new_quota,
                            department=lead_department,
                            is_leader=True,
                        ).on_behalf_of(request.user)
                    )
                    QuotaAssignment.objects.bulk_create(assignments)
                    # Create reports immediately if the quota is issued in the current month
                    period = Period.objects.filter(year=issued_at.year, month=issued_at.month).first()
                    if period:
                        reports = [
                            QuotaReport(
                                quota=new_quota,
                                department=assigned_department,
                                period=period,
                                status=QuotaReport.Status.NOT_SENT,
                            ).on_behalf_of(request.user)
                            for assigned_department in assigned_departments
                        ]
                        QuotaReport.objects.bulk_create(reports)
                    messages.success(request, 'Thêm chỉ tiêu thành công')
        except Exception as e:
            messages.error(request, str(e))
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        return render(
            request, 
            'quota/form.html',
            {
                'name': name,
                'type': type,
                'register_guide': register_guide,
                'submit_guide': submit_guide,
                'target_percent': target_percent,
                'issued_at': issued_at,
                'expired_at': expired_at,
                'lead_department_id': lead_department_id,
                'assigned_department_ids': assigned_department_ids,
                'has_submitted_reports': False,
                'errors': errors,
            },
            status=status,
        )


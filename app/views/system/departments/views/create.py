from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from .....models import Department
from ..query import get_department_create_context

@method_decorator(permission_required('app.add_department'), name='dispatch')
class DepartmentCreateView(View):
    template_name = 'system/departments/create.html'

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            {
                **get_department_create_context(request),
                'errors': {},
                'values': self._empty_values(),
                'short_name_required': True,
                'short_name_disabled': False,
                'name_required': True,
                'type_required': True,
            },
        )

    def post(self, request, *args, **kwargs):
        values = {
            'short_name': (request.POST.get('short_name') or '').strip(),
            'name': (request.POST.get('name') or '').strip(),
            'type': (request.POST.get('type') or '').strip(),
            'is_active': (request.POST.get('is_active') or 'active').strip() or 'active',
            'parent_id': (request.POST.get('parent_id') or '').strip(),
            'parent_cleared': bool((request.POST.get('parent_cleared') or '').strip()),
            'department_id': '',
        }
        errors = {}

        if not values['short_name']:
            errors['short_name'] = 'Mã đơn vị là bắt buộc'
        if not values['name']:
            errors['name'] = 'Tên đơn vị là bắt buộc'
        if values['type'] not in dict(Department.Type.choices):
            errors['type'] = 'Loại đơn vị là bắt buộc'
        if values['is_active'] not in {'active', 'inactive'}:
            errors['is_active'] = 'Trạng thái không hợp lệ'

        parent = None
        if values['parent_id']:
            if not values['parent_id'].isdigit():
                errors['parent_id'] = 'Đơn vị cha không hợp lệ'
            else:
                parent = Department.objects.filter(id=values['parent_id']).first()
                if not parent:
                    errors['parent_id'] = 'Đơn vị cha không tồn tại'
        values['parent_name'] = parent.name if parent else 'Chọn đơn vị cha'

        if errors:
            return render(
                request,
                'system/departments/form.html',
                {
                    **get_department_create_context(request),
                    'errors': errors,
                    'values': values,
                    'short_name_required': True,
                    'short_name_disabled': False,
                    'name_required': True,
                    'type_required': True,
                },
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        with transaction.atomic():
            Department.objects.create(
                short_name=values['short_name'] or None,
                name=values['name'],
                type=values['type'],
                is_active=values['is_active'] == 'active',
                parent=parent,
                created_by=request.user.username,
                updated_by=request.user.username,
            )
            messages.success(request, 'Thêm đơn vị thành công')

        response = render(
            request,
            'system/departments/form.html',
            {
                **get_department_create_context(request),
                'errors': {},
                'values': self._empty_values(),
                'short_name_required': True,
                'short_name_disabled': False,
                'name_required': True,
                'type_required': True,
            },
            status=HTTPStatus.OK,
        )
        response['HX-Trigger-After-Swap'] = 'department:success'
        return response

    def _empty_values(self):
        return {
            'department_id': '',
            'short_name': '',
            'name': '',
            'type': Department.Type.CAX,
            'is_active': 'active',
            'parent_id': '',
            'parent_name': 'Chọn đơn vị cha',
            'parent_cleared': False,
        }

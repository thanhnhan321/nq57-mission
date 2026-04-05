from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from .....models import Department
from ..query import get_department_create_context


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('app.add_department', raise_exception=True), name='dispatch')
class DepartmentCreateView(View):
    template_name = 'system/departments/create.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {**get_department_create_context(request), 'errors': {}, 'values': self._empty_values()})

    def post(self, request, *args, **kwargs):
        values = {
            'short_name': (request.POST.get('short_name') or '').strip(),
            'name': (request.POST.get('name') or '').strip(),
            'type': (request.POST.get('type') or '').strip(),
            'parent_id': (request.POST.get('parent_id') or '').strip(),
        }
        errors = {}

        if not values['name']:
            errors['name'] = 'Tên đơn vị là bắt buộc'
        if values['type'] not in dict(Department.Type.choices):
            errors['type'] = 'Loại đơn vị là bắt buộc'

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
                self.template_name,
                {**get_department_create_context(request), 'errors': errors, 'values': values},
                status=422,
            )

        with transaction.atomic():
            Department.objects.create(
                short_name=values['short_name'] or None,
                name=values['name'],
                type=values['type'],
                parent=parent,
            )
            messages.success(request, 'Thêm đơn vị thành công')

        return render(
            request,
            self.template_name,
            {**get_department_create_context(request), 'errors': {}, 'values': self._empty_values()},
            status=200,
        )

    def _empty_values(self):
        return {
            'short_name': '',
            'name': '',
            'type': Department.Type.CAX,
            'parent_id': '',
            'parent_name': 'Chọn đơn vị cha',
        }

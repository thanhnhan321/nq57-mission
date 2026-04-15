from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from .....models import Department
from ..query import get_department_create_context

@method_decorator(permission_required('app.change_department'), name='dispatch')
class DepartmentUpdateView(View):
    template_name = 'system/departments/update.html'

    def get(self, request, *args, **kwargs):
        department = self._get_department((request.GET.get('id') or '').strip())
        if not department:
            messages.warning(request, 'Đơn vị không tồn tại')
            return self._redirect_to_list()

        return render(request, self.template_name, self._get_form_context(request, department))

    def post(self, request, *args, **kwargs):
        department = self._get_department((request.POST.get('department_id') or request.POST.get('id') or '').strip())
        if not department:
            messages.warning(request, 'Đơn vị không tồn tại')
            return self._redirect_to_list()

        values = {
            'department_id': str(department.id),
            'short_name': department.short_name or '',
            'name': (request.POST.get('name') or '').strip(),
            'type': (request.POST.get('type') or '').strip(),
            'is_active': (request.POST.get('is_active') or ('active' if department.is_active else 'inactive')).strip() or ('active' if department.is_active else 'inactive'),
            'parent_id': (request.POST.get('parent_id') or '').strip(),
            'parent_cleared': bool((request.POST.get('parent_cleared') or '').strip()),
        }
        errors = {}

        parent = department.parent
        if values['parent_id']:
            if not values['parent_id'].isdigit():
                errors['parent_id'] = 'Đơn vị cha không hợp lệ'
            else:
                parent = Department.objects.select_related('parent').filter(id=values['parent_id']).first()
                if not parent:
                    errors['parent_id'] = 'Đơn vị cha không tồn tại'
                elif str(parent.id) == str(department.id):
                    errors['parent_id'] = 'Đơn vị cha không hợp lệ'
                else:
                    ancestor = parent.parent
                    while ancestor:
                        if str(ancestor.id) == str(department.id):
                            errors['parent_id'] = 'Đơn vị cha không hợp lệ'
                            parent = department.parent
                            break
                        ancestor = ancestor.parent
        elif values['parent_cleared']:
            parent = None

        if values['type'] and values['type'] not in dict(Department.Type.choices):
            errors['type'] = 'Loại đơn vị không hợp lệ'
        if values['is_active'] not in {'active', 'inactive'}:
            errors['is_active'] = 'Trạng thái không hợp lệ'

        context = self._get_form_context(request, department, values=values, errors=errors, parent=parent)

        if errors:
            return render(request, 'system/departments/update_form.html', context, status=HTTPStatus.UNPROCESSABLE_ENTITY)

        try:
            with transaction.atomic():
                department.name = values['name'] or department.name
                department.type = values['type'] or department.type
                department.parent = parent
                department.is_active = values['is_active'] == 'active'
                department.save(user=request.user)
                if values['is_active'] == 'inactive':
                    self._lock_department_tree(department, request.user)
                messages.success(request, 'Cập nhật đơn vị thành công')
        except Exception as exc:
            messages.error(request, str(exc))
            return render(request, 'system/departments/update_form.html', context, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        refreshed_department = self._get_department(str(department.id)) or department
        response = render(
            request,
            'system/departments/update_form.html',
            self._get_form_context(request, refreshed_department),
            status=HTTPStatus.OK,
        )
        response['HX-Trigger-After-Swap'] = 'department:success'
        return response

    def _get_department(self, department_id):
        if not department_id.isdigit():
            return None
        return Department.objects.select_related('parent').filter(id=department_id).first()

    def _collect_subtree_departments(self, department):
        collected = [department]
        queue = [department]
        while queue:
            current = queue.pop(0)
            children = list(Department.objects.select_related('parent').filter(parent_id=current.id))
            collected.extend(children)
            queue.extend(children)
        return collected

    def _lock_department_tree(self, department, user):
        subtree = self._collect_subtree_departments(department)
        for subtree_department in subtree:
            if subtree_department.id == department.id:
                continue
            subtree_department.is_active = False
            subtree_department.save(user=user)
        subtree_ids = [item.id for item in subtree]
        User.objects.filter(profile__department_id__in=subtree_ids).update(is_active=False)

    def _get_form_context(self, request, department, values=None, errors=None, parent=None):
        parent = department.parent if parent is None and department.parent else parent
        return {
            **get_department_create_context(request),
            'values': values or self._default_values(department, parent),
            'errors': errors or {},
            'short_name_required': False,
            'short_name_disabled': True,
            'name_required': False,
            'type_required': False,
        }

    def _default_values(self, department, parent=None):
        parent = parent if parent is not None else department.parent
        return {
            'department_id': str(department.id),
            'short_name': department.short_name or '',
            'name': department.name or '',
            'type': department.type,
            'is_active': 'active' if department.is_active else 'inactive',
            'parent_id': str(parent.id) if parent else '',
            'parent_name': parent.name if parent else 'Chọn đơn vị cha',
            'parent_cleared': False,
        }

    def _redirect_to_list(self):
        response = HttpResponse()
        response['HX-Redirect'] = reverse('department_list')
        return response
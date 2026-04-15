from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from .....models import Department, UserProfile
from ..context import build_department_tree_context
from ..state import apply_default_user_state, apply_role_state
from ..table import DEFAULT_GROUP_NAME
from ..validators import validate_password, validate_phone, validate_username


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('auth.add_user', raise_exception=True), name='dispatch')
class UserCreateView(View):
    template_name = 'system/users/create.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self._get_form_context())

    def post(self, request, *args, **kwargs):
        context = self._get_form_context(request)
        errors = {}

        username = (request.POST.get('username') or '').strip()
        full_name = (request.POST.get('full_name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        password = request.POST.get('password') or ''
        department_id = (request.POST.get('department_id') or '').strip()
        is_admin = bool(request.POST.get('is_admin'))

        username_error = validate_username(username)
        if username_error:
            errors['username'] = username_error
        elif User.objects.filter(username__iexact=username).exists():
            errors['username'] = 'Tên đăng nhập đã tồn tại'

        if not full_name:
            errors['full_name'] = 'Họ tên là bắt buộc'

        if email and '@' not in email:
            errors['email'] = 'Email không hợp lệ'

        phone_error = validate_phone(phone)
        if phone_error:
            errors['phone'] = phone_error

        if not password:
            errors['password'] = 'Mật khẩu là bắt buộc'
        else:
            password_error = validate_password(password)
            if password_error:
                errors['password'] = password_error

        if not department_id.isdigit():
            errors['department_id'] = 'Đơn vị là bắt buộc'

        department = Department.objects.filter(id=department_id).first() if department_id.isdigit() else None
        if department_id.isdigit() and not department:
            errors['department_id'] = 'Đơn vị không tồn tại'
        department_name = department.name if department else 'Chọn đơn vị'

        context.update(
            {
                'username': username,
                'full_name': full_name,
                'email': email,
                'phone': phone,
                'password': password,
                'department_id': department_id,
                'department_name': department_name,
                'is_admin': is_admin,
                'errors': errors,
            }
        )

        if errors:
            return render(request, 'system/users/form.html', context, status=HTTPStatus.UNPROCESSABLE_ENTITY)

        try:
            with transaction.atomic():
                user = User(username=username, email=email, is_staff=True, is_superuser=is_admin)
                user.set_password(password)
                user.save()
                apply_default_user_state(user, DEFAULT_GROUP_NAME)
                apply_role_state(user, is_admin=is_admin)

                UserProfile.objects.create(
                    user=user,
                    full_name=full_name,
                    phone=phone,
                    department=department,
                )

                messages.success(request, 'Thêm người dùng thành công')
        except Exception as exc:
            messages.error(request, str(exc))

        return render(request, 'system/users/form.html', self._get_form_context(), status=HTTPStatus.OK)

    def _get_form_context(self, request=None):
        return {
            **build_department_tree_context(),
            'username': '',
            'full_name': '',
            'email': '',
            'phone': '',
            'password': '',
            'department_id': '',
            'department_name': 'Chọn đơn vị',
            'is_admin': False,
            'errors': {},
        }

from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from ..extractors import get_full_name
from ..validators import validate_password


@method_decorator(permission_required('auth.change_user'), name='dispatch')
class UserUpdateView(View):
    template_name = 'system/users/update.html'

    def get(self, request, *args, **kwargs):
        user_id = (request.GET.get('id') or '').strip()
        user = self._get_user(user_id)
        if not user:
            messages.warning(request, 'Người dùng không tồn tại')
            return self._redirect_to_list()

        return render(request, self.template_name, self._get_form_context(user))

    def post(self, request, *args, **kwargs):
        user_id = (request.POST.get('user_id') or '').strip()
        user = self._get_user(user_id)
        if not user:
            messages.warning(request, 'Người dùng không tồn tại')
            return self._redirect_to_list()

        password = request.POST.get('password') or ''
        is_active = (request.POST.get('is_active') or '').strip()

        errors = {}
        if password:
            password_error = validate_password(password)
            if password_error:
                errors['password'] = password_error

        if is_active and is_active not in {'active', 'inactive'}:
            errors['is_active'] = 'Trạng thái không hợp lệ'

        context = self._get_form_context(
            user,
            password=password,
            is_active=is_active or ('active' if user.is_active else 'inactive'),
            errors=errors,
        )

        if errors:
            return render(request, 'system/users/update_form.html', context, status=HTTPStatus.UNPROCESSABLE_ENTITY)

        try:
            with transaction.atomic():
                update_fields = []
                if password:
                    user.set_password(password)
                    update_fields.append('password')

                if is_active in {'active', 'inactive'}:
                    user.is_active = is_active == 'active'
                    update_fields.append('is_active')

                if update_fields:
                    user.save(update_fields=update_fields)
                messages.success(request, 'Cập nhật người dùng thành công')
        except Exception as exc:
            messages.error(request, str(exc))

        return render(request, 'system/users/update_form.html', self._get_form_context(user), status=HTTPStatus.OK)

    def _get_user(self, user_id):
        if not user_id.isdigit():
            return None
        return User.objects.select_related('profile').filter(id=int(user_id)).first()

    def _get_form_context(self, user, password='', is_active=None, errors=None):
        full_name = get_full_name(user)

        selected_status = ('active' if user.is_active else 'inactive') if is_active is None else is_active

        return {
            'user_id': user.id,
            'username': user.username,
            'full_name': full_name,
            'password': password,
            'is_active': selected_status,
            'errors': errors or {},
        }

    def _redirect_to_list(self):
        from django.http import HttpResponse

        response = HttpResponse()
        response['HX-Redirect'] = reverse('user_list')
        return response

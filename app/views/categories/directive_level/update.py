from http import HTTPStatus
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required

from ....models.document import DirectiveLevel
from ....handlers.directive_level import DIRECTIVE_LEVELS_KEY
from ....utils.cache import cache

@method_decorator(permission_required('app.change_directivelevel'), name='dispatch')
class DirectiveLevelUpdateView(View):
    template_name = 'categories/directive_level/update.html'

    def get(self, request, *args, **kwargs):
        id = request.GET.get('id', '').strip()
        response = HttpResponse()
        response['HX-Redirect'] = reverse('directive_level_list')
        if not id.isdigit():
            messages.warning(request, 'Chưa chọn cấp chỉ đạo')
            return response
        directive_level = DirectiveLevel.objects.filter(id=id).first()
        if not directive_level:
            messages.warning(request, 'Cấp chỉ đạo không tồn tại')
            return response
        return render(
            request,
            self.template_name,
            {
                'id': id,
                'name': directive_level.name,
                'description': directive_level.description,
                'errors': {},
            },
            status=HTTPStatus.OK
        )

    def post(self, request, *args, **kwargs):
        errors = {}
        status = HTTPStatus.OK
        response = HttpResponse()
        response['HX-Redirect'] = reverse('directive_level_list')
        id = request.POST.get('id', '').strip()
        if not id:
            messages.warning(request, 'Chưa chọn cấp chỉ đạo')
            return response
        name = request.POST.get('name', "").strip()
        if not name:
            errors['name'] = 'Mã cấp chỉ đạo không được để trống'
        description = request.POST.get('description', "").strip()
        if not description:
            errors['description'] = 'Tên cấp chỉ đạo không được để trống'
        if errors:
            return render(
                request,
                'categories/directive_level/form.html',
                {
                    'id': id,
                    'name': name,
                    'description': description,
                    'errors': errors,
                },
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        try:
            directive_level = DirectiveLevel.objects.filter(id=id).first()
            if not directive_level:
                messages.warning(request, 'Cấp chỉ đạo không tồn tại')
                return response
            name = name.upper()
            existed = DirectiveLevel.objects.filter(Q(name=name) & ~Q(id=id)).exists()
            if existed:
                errors['name'] = 'Mã cấp chỉ đạo đã tồn tại'
                status = HTTPStatus.UNPROCESSABLE_ENTITY
            else:
                directive_level.name = name
                directive_level.description = description
                directive_level.save(user=request.user)
                cache.delete(DIRECTIVE_LEVELS_KEY)
                messages.success(request, 'Cập nhật cấp chỉ đạo thành công')
        except Exception as e:
            messages.error(request, str(e))
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        return render(
            request, 
            'categories/directive_level/form.html',
            {
                'id': id,
                'name': name,
                'description': description,
                'errors': errors,
            },
            status=status,
        )


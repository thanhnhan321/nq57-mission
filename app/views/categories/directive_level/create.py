from http import HTTPStatus
from django.contrib import messages
from django.shortcuts import render
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required

from ....models.document import DirectiveLevel
from ....handlers.directive_level import DIRECTIVE_LEVELS_KEY
from ....utils.cache import cache

@method_decorator(permission_required('app.add_directivelevel'), name='dispatch')
class DirectiveLevelCreateView(View):
    template_name = 'categories/directive_level/create.html'

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            {
                'name': '',
                'description': '',
                'errors': {},
            }
        )

    def post(self, request, *args, **kwargs):
        errors = {}
        status = HTTPStatus.OK
        name = request.POST.get('name', "").strip()
        if not name:
            errors['name'] = 'Mã cấp chỉ đạo là bắt buộc'
        description = request.POST.get('description', "").strip()
        if not description:
            errors['description'] = 'Tên cấp chỉ đạo là bắt buộc'
        if errors:
            return render(
                request,
                'categories/directive_level/form.html',
                {
                    'name': name,
                    'description': description,
                    'errors': errors,
                },
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        try:
            name = name.upper()
            existed = DirectiveLevel.objects.filter(name=name).exists()
            if existed:
                errors['name'] = 'Mã cấp chỉ đạo đã tồn tại'
                status = HTTPStatus.UNPROCESSABLE_ENTITY
            else:
                new_directive_level = DirectiveLevel(
                    name=name,
                    description=description,
                )
                new_directive_level.save(user=request.user)
                cache.delete(DIRECTIVE_LEVELS_KEY)
                messages.success(request, 'Thêm cấp chỉ đạo thành công')
        except Exception as e:
            messages.error(request, str(e))
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        return render(
            request, 
            'categories/directive_level/form.html',
            {
                'name': name,
                'description': description,
                'errors': errors,
            },
            status=status,
        )


from http import HTTPStatus

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required

from ....models import DirectiveDocument, DirectiveLevel, DocumentType
from ....handlers.directive_level import DIRECTIVE_LEVELS_KEY
from ....utils.cache import cache
@method_decorator(permission_required('app.change_directivedocument'), name='dispatch')
class DirectiveDocumentUpdateView(View):
    template_name = 'categories/directive_document/update.html'

    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', '').strip()
        if not code:
            messages.warning(request, 'Chưa chọn văn bản chỉ đạo')
            response = HttpResponse()
            response['HX-Redirect'] = reverse('directive_document_list')
            return response
        directive_document = DirectiveDocument.objects.filter(code=code).first()
        if not directive_document:
            messages.warning(request, 'Văn bản chỉ đạo không tồn tại')
            response = HttpResponse()
            response['HX-Redirect'] = reverse('directive_document_list')
            return response
        return render(
            request,
            self.template_name,
            {
                'code': code,
                'title': directive_document.title,
                'type_code': directive_document.type_id,
                'level_id': directive_document.directive_level_id,
                'issued_at': directive_document.issued_at,
                'valid_from': directive_document.valid_from,
                'valid_to': directive_document.valid_to,
                'errors': {},
            }
        )

    def post(self, request, *args, **kwargs):
        errors = {}
        status = HTTPStatus.OK
        response = HttpResponse()
        response['HX-Redirect'] = reverse('directive_document_list')
        code = request.POST.get('code', '').strip()
        if not code:
            messages.warning(request, 'Chưa chọn văn bản chỉ đạo')
            return response
        title = request.POST.get('title', "").strip()
        if not title:
            errors['title'] = 'Tên văn bản chỉ đạo là bắt buộc'
        type_code = request.POST.get('type_code', "").strip()
        if not type_code:
            errors['type_code'] = 'Loại văn bản là bắt buộc'
        level_id = request.POST.get('level_id', "").strip()
        if not level_id.isdigit():
            errors['level_id'] = 'Cấp chỉ đạo là bắt buộc'
        else:
            level_id = int(level_id)
        issued_at = request.POST.get('issued_at', "").strip()
        if not issued_at:
            errors['issued_at'] = 'Ngày ban hành là bắt buộc'
        valid_from = request.POST.get('valid_from', "").strip()
        if not valid_from:
            errors['valid_from'] = 'Ngày hiệu lực là bắt buộc'
        valid_to = request.POST.get('valid_to', "").strip()
        if errors:
            return render(
                request,
                'directive_document/form.html',
                {
                    'code': code,
                    'title': title,
                    'type_code': type_code,
                    'level_id': level_id,
                    'issued_at': issued_at,
                    'valid_from': valid_from,
                    'valid_to': valid_to,
                    'errors': errors,
                },
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        try:
            issued_at = parse_date(issued_at)
            valid_from = parse_date(valid_from)
            valid_to = parse_date(valid_to)
            if valid_to:
                if valid_from > valid_to:
                    errors['valid_to'] = 'Ngày hết hiệu lực không được nhỏ hơn ngày hiệu lực'
            type = DocumentType.objects.filter(code=type_code).first()
            if not type:
                errors['type_id'] = 'Loại văn bản không tồn tại'
            level = DirectiveLevel.objects.filter(id=level_id).first()
            if not level:
                errors['level_id'] = 'Cấp chỉ đạo không tồn tại'
            if errors:
                status = HTTPStatus.UNPROCESSABLE_ENTITY
            else:
                directive_document = DirectiveDocument.objects.filter(code=code).first()
                if not directive_document:
                    messages.warning(request, 'Văn bản chỉ đạo không tồn tại')
                    return response
                with transaction.atomic():
                    directive_document.title = title
                    directive_document.type = type
                    directive_document.level = level
                    directive_document.issued_at = issued_at
                    directive_document.valid_from = valid_from
                    directive_document.valid_to = valid_to
                    directive_document.save(user=request.user)
                    cache.delete(DIRECTIVE_LEVELS_KEY)
                    messages.success(request, 'Cập nhật văn bản chỉ đạo thành công')
        except Exception as e:
            messages.error(request, str(e))
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        return render(
            request, 
            'directive_document/form.html',
            {
                'code': code,
                'title': title,
                'type_code': type_code,
                'level_id': level_id,
                'issued_at': issued_at,
                'valid_from': valid_from,
                'valid_to': valid_to,
                'errors': errors,
            },
            status=status,
        )


from http import HTTPStatus

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render
from django.views import View
from django.utils.decorators import method_decorator
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import permission_required

from ....models import DirectiveDocument, DirectiveLevel, DocumentType, Storage
from ....handlers.directive_level import DIRECTIVE_LEVELS_KEY
from ....utils.cache import cache
from utils import minio

@method_decorator(permission_required('app.add_directivedocument'), name='dispatch')
class DirectiveDocumentCreateView(View):
    template_name = 'categories/directive_document/create.html'
    form_template_name = 'categories/directive_document/form.html'

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            {
                'code': '',
                'title': '',
                'type_code': '',
                'level_id': '',
                'issued_at': '',
                'valid_from': '',
                'valid_to': '',
                'errors': {},
            }
        )

    def post(self, request, *args, **kwargs):
        errors = {}
        status = HTTPStatus.OK
        code = request.POST.get('code', "").strip()
        if not code:
            errors['code'] = 'Số văn bản chỉ đạo là bắt buộc'
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
            errors['valid_from'] = 'Ngày bắt đầu là bắt buộc'
        valid_to = request.POST.get('valid_to', "").strip()
        object = request.FILES.get('object', None)
        if not object:
            errors['object'] = 'Vui lòng tải lên file đính kèm'
        if errors:
            return render(
                request,
                self.form_template_name,
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
            level_id = int(level_id)
            level = DirectiveLevel.objects.filter(id=level_id).first()
            if not level:
                errors['level_id'] = 'Cấp chỉ đạo không tồn tại'
            directive_document_exists = DirectiveDocument.objects.filter(code=code).exists()
            if directive_document_exists:
                errors['code'] = 'Số văn bản chỉ đạo đã tồn tại'
            if errors:
                status = HTTPStatus.UNPROCESSABLE_ENTITY
            else:
                with transaction.atomic():
                    new_object = Storage(
                        file_name=object.name,
                        size=object.size,
                    )
                    new_object.save(user=request.user)
                    minio.upload(object, new_object.object_uid)
                    new_directive_document = DirectiveDocument(
                        code=code,
                        title=title,
                        type=type,
                        directive_level=level,
                        issued_at=issued_at,
                        valid_from=valid_from,
                        valid_to=valid_to or None,
                        object=new_object,
                    )
                    new_directive_document.save(user=request.user)
                    cache.delete(DIRECTIVE_LEVELS_KEY)
                    messages.success(request, 'Thêm văn bản chỉ đạo thành công')
        except Exception as e:
            messages.error(request, str(e))
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        return render(
            request, 
            self.form_template_name,
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


from http import HTTPStatus
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required

from ....models.document import DocumentType

@method_decorator(permission_required('app.add_documenttype'), name='dispatch')
class DocumentTypeCreateView(View):
    template_name = 'categories/document_type/create.html'

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            {
                'code': '',
                'name': '',
                'errors': {},
            }
        )

    def post(self, request, *args, **kwargs):
        errors = {}
        status = HTTPStatus.OK
        code = request.POST.get('code', "").strip()
        if not code:
            errors['code'] = 'Mã loại văn bản là bắt buộc'
        name = request.POST.get('name', "").strip()
        if not name:
            errors['name'] = 'Tên loại văn bản là bắt buộc'
        if errors:
            return render(
                request,
                'categories/document_type/form.html',
                {
                    'name': name,
                    'code': code,
                    'errors': errors,
                },
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        try:
            code = code.upper()
            document_type = DocumentType.objects.filter(Q(code=code) | Q(name=name)).first()
            if document_type:
                status = HTTPStatus.UNPROCESSABLE_ENTITY
                if document_type.code == code:
                    errors['code'] = 'Mã loại văn bản đã tồn tại'
                else:
                    errors['name'] = 'Tên loại văn bản đã tồn tại'
            else:
                new_document_type = DocumentType(
                    name=name,
                    code=code,
                )
                new_document_type.save(user=request.user)
                messages.success(request, 'Thêm loại văn bản thành công')
        except Exception as e:
            messages.error(request, str(e))
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        return render(
            request, 
            'categories/document_type/form.html',
            {
                'name': name,
                'code': code,
                'errors': errors,
            },
            status=status,
        )


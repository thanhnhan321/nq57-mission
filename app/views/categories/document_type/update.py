from http import HTTPStatus
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required

from ....models.document import DocumentType

@method_decorator(permission_required('app.change_documenttype'), name='dispatch')
class DocumentTypeUpdateView(View):
    template_name = 'categories/document_type/update.html'

    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', '').strip()
        response = HttpResponse()
        response['HX-Redirect'] = reverse('document_type_list')
        if not code:
            messages.warning(request, 'Chưa chọn loại văn bản')
            return response
        document_type = DocumentType.objects.filter(code=code).first()
        if not document_type:
            messages.warning(request, 'Loại văn bản không tồn tại')
            return response
        return render(
            request,
            self.template_name,
            {
                'code': code,
                'name': document_type.name,
                'errors': {},
            },
            status=HTTPStatus.OK
        )

    def post(self, request, *args, **kwargs):
        errors = {}
        status = HTTPStatus.OK
        response = HttpResponse()
        response['HX-Redirect'] = reverse('document_type_list')
        code = request.POST.get('code', '').strip()
        if not code:
            messages.warning(request, 'Chưa chọn loại văn bản')
            return response
        name = request.POST.get('name', "").strip()
        if not name:
            errors['name'] = 'Tên loại văn bản là bắt buộc'
        if errors:
            return render(
                request,
                'categories/document_type/form.html',
                {
                    'code': code,
                    'name': name,
                    'errors': errors,
                },
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        try:
            document_type = DocumentType.objects.filter(code=code).first()
            if not document_type:
                messages.warning(request, 'Loại văn bản không tồn tại')
                return response
            name_exists = DocumentType.objects.filter(Q(name=name) & ~Q(code=code)).exists()
            if name_exists:
                errors['name'] = 'Tên loại văn bản đã tồn tại'
                status = HTTPStatus.UNPROCESSABLE_ENTITY
            else:
                document_type.name = name
                document_type.save(user=request.user)
                messages.success(request, 'Cập nhật loại văn bản thành công')
        except Exception as e:
            messages.error(request, str(e))
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        return render(
            request, 
            'categories/document_type/form.html',
            {
                'code': code,
                'name': name,
                'errors': errors,
            },
            status=status,
        )


from http import HTTPStatus
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

from ....models.document import DocumentType, Document, DirectiveDocument

@method_decorator(permission_required('app.delete_documenttype'), name='dispatch')
class DocumentTypeDeleteView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', '').strip()
        if not code:
            messages.warning(request, 'Chưa chọn loại văn bản')
            return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Chưa chọn loại văn bản'})
        try:
            directive_doc_exists = DirectiveDocument.objects.filter(type_id=code).exists()
            if directive_doc_exists:
                messages.warning(request, 'Có văn bản chỉ đạo thuộc loại văn bản này, không thể xóa')
                return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Có văn bản chỉ đạo thuộc loại văn bản này, không thể xóa'})
            document_exists = Document.objects.filter(type_id=code).exists()
            if document_exists:
                messages.warning(request, 'Có văn bản thuộc loại văn bản này, không thể xóa')
                return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Có văn bản thuộc loại văn bản này, không thể xóa'})
            document_type = DocumentType.objects.filter(code=code).first()
            if not document_type:
                messages.warning(request, 'Loại văn bản không tồn tại')
                return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Loại văn bản không tồn tại'})
            document_type.delete()
            messages.success(request, 'Xóa loại văn bản thành công')
        except Exception as e:
            messages.error(request, str(e))
            return JsonResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR, data={'message': str(e)})
        return JsonResponse(status=HTTPStatus.OK, data={'message': 'Xóa cấp chỉ đạo thành công'})
from http import HTTPStatus
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

from ...models import DirectiveDocument, Mission

@method_decorator(permission_required('app.delete_directivedocument'), name='dispatch')
class DirectiveDocumentDeleteView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', '')
        if not code:
            messages.warning(request, 'Chưa chọn văn bản chỉ đạo')
            return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Chưa chọn văn bản chỉ đạo'})
        try:
            directive_document = DirectiveDocument.objects.filter(code=code).first()
            if not directive_document:
                messages.warning(request, 'Văn bản chỉ đạo không tồn tại')
                return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Văn bản chỉ đạo không tồn tại'})
            task_exists = Mission.objects.filter(directive_document_id=code).exists()
            if task_exists:
                messages.warning(request, 'Văn bản chỉ đạo đã được sử dụng trong nhiệm vụ, không thể xóa')
                return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Văn bản chỉ đạo đã được sử dụng trong nhiệm vụ, không thể xóa'})
            directive_document.delete()
            messages.success(request, 'Xóa văn bản chỉ đạo thành công')
        except Exception as e:
            messages.error(request, str(e))
            return JsonResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR, data={'message': str(e)})
        return JsonResponse(status=HTTPStatus.OK, data={'message': 'Xóa cấp chỉ đạo thành công'})
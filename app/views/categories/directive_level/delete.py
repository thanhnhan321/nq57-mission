from http import HTTPStatus
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

from ....models.document import DirectiveLevel, DirectiveDocument

@method_decorator(permission_required('app.delete_directivelevel'), name='dispatch')
class DirectiveLevelDeleteView(View):
    def get(self, request, *args, **kwargs):
        id = request.GET.get('id', '').strip()
        if not id or not id.isdigit():
            messages.warning(request, 'Chưa chọn cấp chỉ đạo')
            return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Chưa chọn cấp chỉ đạo'})
        try:
            directive_doc_exists = DirectiveDocument.objects.filter(directive_level_id=id).exists()
            if directive_doc_exists:
                messages.warning(request, 'Có văn bản chỉ đạo thuộc cấp chỉ đạo này, không thể xóa')
                return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Có văn bản chỉ đạo thuộc cấp chỉ đạo này, không thể xóa'})
            directive_level = DirectiveLevel.objects.filter(id=id).first()
            if not directive_level:
                messages.warning(request, 'Cấp chỉ đạo không tồn tại')
                return JsonResponse(status=HTTPStatus.UNPROCESSABLE_ENTITY, data={'message': 'Cấp chỉ đạo không tồn tại'})
            directive_level.delete()
            messages.success(request, 'Xóa cấp chỉ đạo thành công')
        except Exception as e:
            messages.error(request, str(e))
            return JsonResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR, data={'message': str(e)})
        return JsonResponse(status=HTTPStatus.OK, data={'message': 'Xóa cấp chỉ đạo thành công'})
from django.contrib import messages
from django.http import FileResponse, HttpResponse
from django.urls import reverse
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required

import env

from ...models import DirectiveDocument
from utils import minio

@method_decorator(permission_required('app.view_directivedocument'), name='dispatch')
class DirectiveDocumentDownloadView(View):
    
    def get(self, request, *args, **kwargs):
        response = HttpResponse()
        code = request.GET.get('code', '')
        if not code:
            messages.warning(request, 'Chưa chọn văn bản chỉ đạo')
            response['HX-Redirect'] = reverse('directive_document_list')
            return response
        directive_document = DirectiveDocument.objects.filter(code=code).values('object_id', 'object__file_name').first()
        if not directive_document:
            messages.warning(request, 'Văn bản chỉ đạo không tồn tại')
            return response
        try:
            object_response = minio.download(directive_document['object_id'])
        except Exception:
            messages.warning(request, 'Không thể tải văn bản chỉ đạo')
            return response
        response =FileResponse(
            object_response,
            as_attachment=True,
            filename=directive_document['object__file_name'],
        )
        return response
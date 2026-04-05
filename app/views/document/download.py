from django.contrib import messages
from django.http import FileResponse, HttpResponse
from django.urls import reverse
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required

import env

from ...models import Document
from utils import minio


@method_decorator(permission_required('app.read_document'), name='dispatch')
class DocumentDownloadView(View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse()
        is_htmx = request.headers.get('HX-Request') == 'true'

        if is_htmx:
            params = request.GET.urlencode()
            response['HX-Redirect'] = env.HOST_URL + request.path + ('?' + params if params else '')
            return response
        else:
            response['HX-Redirect'] = reverse('document_list')

        code = request.GET.get('code', '').strip()
        if not code:
            messages.warning(request, 'Chưa chọn văn bản')
            return response

        document = Document.objects.filter(code=code).first()
        if not document:
            messages.warning(request, 'Văn bản không tồn tại')
            return response

        object_response = minio.download(document.object_id)
        if object_response.status != 200:
            messages.warning(request, 'Không thể tải văn bản')
            return response

        return FileResponse(
            object_response,
            as_attachment=True,
            filename=document.object.file_name,
        )
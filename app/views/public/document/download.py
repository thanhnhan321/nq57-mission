from django.contrib import messages
from django.http import FileResponse, HttpResponse
from django.urls import reverse
from django.views import View

import env

from ....models import Document
from utils import minio

class PublicDocumentDownloadView(View):
    
    def get(self, request, *args, **kwargs):
        response = HttpResponse()
        response['HX-Redirect'] = reverse('public_document_list')
        code = request.GET.get('code', '')
        if not code:
            messages.warning(request, 'Chưa chọn văn bản')
            return response
        document = Document.objects.filter(code=code).values('object_id', 'object__file_name').first()
        if not document:
            messages.warning(request, 'Văn bản không tồn tại')
            return response
        try:
            object_response = minio.download(document['object_id'])
        except Exception:
            messages.warning(request, 'Không thể tải văn bản')
            return response
    
        response =FileResponse(
            object_response,
            as_attachment=True,
            filename=document['object__file_name'],
        )
        return response
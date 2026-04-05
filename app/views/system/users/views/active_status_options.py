from django.http import JsonResponse
from django.views import View


class UserActiveStatusOptionsView(View):
    def get(self, request, *args, **kwargs):
        options = [
            {'value': 'active', 'label': 'Hoạt động'},
            {'value': 'inactive', 'label': 'Tạm khóa'},
        ]
        return JsonResponse(options, safe=False)

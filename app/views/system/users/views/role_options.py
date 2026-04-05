from django.http import JsonResponse
from django.views import View


class UserRoleOptionsView(View):
    def get(self, request, *args, **kwargs):
        options = [
            {'value': 'admin', 'label': 'Quản trị viên'},
            {'value': 'member', 'label': 'Thành viên'},
        ]
        return JsonResponse(options, safe=False)

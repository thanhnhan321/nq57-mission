from http import HTTPStatus
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required

from ....models.rank import Ranking


@method_decorator(permission_required('app.change_ranking'), name='dispatch')
class RankingUpdateView(View):
    template_name = 'leader/rank/update.html'

    def get(self, request, *args, **kwargs):
        id = request.GET.get('id', '').strip()

        response = HttpResponse()
        response['HX-Redirect'] = reverse('ranking_list')

        if not id:
            messages.warning(request, 'Chưa chọn xếp loại')
            return response

        obj = Ranking.objects.filter(id=id).first()
        if not obj:
            messages.warning(request, 'Xếp loại không tồn tại')
            return response

        return render(request, self.template_name, {
            'code': obj.code,
            'name': obj.name,
            'score_from': obj.score_from,
            'score_to': obj.score_to,
            'description': obj.description,
            'errors': {},
        })

    def post(self, request, *args, **kwargs):
        errors = {}
        status = HTTPStatus.OK

        code = request.POST.get('code', '').strip()
        name = request.POST.get('name', '').strip()
        score_from = request.POST.get('score_from', '').strip()
        score_to = request.POST.get('score_to', '').strip()
        description = request.POST.get('description', '').strip()

        response = HttpResponse()
        response['HX-Redirect'] = reverse('ranking_list')

        if not code:
            return response

        if not name:
            errors['name'] = 'Tên xếp loại là bắt buộc'

        if not score_from:
            errors['score_from'] = 'Điểm từ là bắt buộc'

        if not score_to:
            errors['score_to'] = 'Điểm đến là bắt buộc'

        if errors:
            return render(
                request,
                'leader/rank/form.html',
                {**request.POST, 'errors': errors},
                status=HTTPStatus.UNPROCESSABLE_ENTITY
            )

        try:
            obj = Ranking.objects.filter(code=code).first()
            if not obj:
                return response

            name_exists = Ranking.objects.filter(
                Q(name=name) & ~Q(code=code)
            ).exists()

            if name_exists:
                errors['name'] = 'Tên xếp loại đã tồn tại'
                status = HTTPStatus.UNPROCESSABLE_ENTITY
            else:
                score_from_val = float(score_from)
                score_to_val = float(score_to)

                if score_from_val > score_to_val:
                    errors['score_to'] = 'Điểm đến phải lớn hơn hoặc bằng điểm từ'
                    status = HTTPStatus.UNPROCESSABLE_ENTITY
                else:
                    overlap = Ranking.objects.filter(
                        score_from__lte=score_to_val,
                        score_to__gte=score_from_val
                    ).exclude(code=code).first()

                    if overlap:
                        errors['score_from'] = (
                            f'Khoảng điểm bị giao với xếp loại "{overlap.name}" '
                            f'({overlap.score_from} - {overlap.score_to})'
                        )
                        errors['score_to'] = errors['score_from']
                        status = HTTPStatus.UNPROCESSABLE_ENTITY
                    else:
                        obj.name = name
                        obj.score_from = score_from_val
                        obj.score_to = score_to_val
                        obj.description = description
                        obj.save()
                        messages.success(request, 'Cập nhật thành công')

        except Exception as e:
            messages.error(request, str(e))
            status = HTTPStatus.INTERNAL_SERVER_ERROR

        return render(
            request,
            'leader/rank/form.html',
            {
                'code': code,
                'name': name,
                'score_from': score_from,
                'score_to': score_to,
                'description': description,
                'errors': errors,
            },
            status=status,
        )
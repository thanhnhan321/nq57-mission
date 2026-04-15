from http import HTTPStatus

from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.contrib import messages
from django.views.decorators.http import require_GET, require_POST
from django.urls import reverse

from ...models.system_config import SystemConfig
from ...handlers.config import get_config


def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_superuser)(view_func)


def _is_quota_locked() -> bool:
    return str(get_config(SystemConfig.Key.QUOTA_LOCK_AFTER_DEADLINE)).lower() != "false"


@require_GET
@superuser_required
def quota_period_toggle_confirm(request):
    is_locked = _is_quota_locked()

    context = {
        "is_locked": is_locked,
        "action_label": "Mở kỳ" if is_locked else "Khóa kỳ",
        "submit_url": reverse("quota_period_toggle"),
    }
    return render(request, "quota/toggle_period_confirm.html", context)


@require_POST
@superuser_required
def quota_period_toggle(request):
    is_locked = _is_quota_locked()
    next_value = "false" if is_locked else "true"
    action_label = "Mở kỳ" if is_locked else "Khóa kỳ"
    try:
        SystemConfig.objects.update_or_create(
            key=SystemConfig.Key.QUOTA_LOCK_AFTER_DEADLINE,
            defaults={
                "value": next_value,
            }
        )

        messages.success(request, f"{action_label} thành công")
        response = HttpResponse(status=204)
        return response
    except Exception as e:
        messages.error(request, str(e))
        return JsonResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR, data={'message': "Lỗi hệ thống"})
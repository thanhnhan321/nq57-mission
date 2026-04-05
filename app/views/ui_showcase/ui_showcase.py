import random
import time

from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render, reverse
from django.views.generic.base import TemplateView

ASSET_TYPE_OPTIONS = [
    {"value": "land", "label": "Đất", "klass": "bg-emerald-600 text-white"},
    {"value": "car", "label": "Ô tô", "klass": "bg-indigo-600 text-white"},
    {"value": "house", "label": "Nhà, vật kiến trúc", "klass": "bg-amber-500 text-white"},
    {"value": "machinery", "label": "Thiết bị máy móc", "klass": "bg-slate-900 text-white"},
    {"value": "other", "label": "Tài sản khác", "klass": "bg-slate-100 text-slate-800"},
    {"value": "perennial", "label": "Cây lâu năm, súc vật làm việc và cho sản phẩm", "klass": "bg-pink-600 text-white"},
    {"value": "long1", "label": "Tài sản cố định hữu hình khác (máy móc, thiết bị, phương tiện vận tải, dụng cụ quản lý) và tài sản cố định vô hình", "klass": "bg-fuchsia-600 text-white"},
    {"value": "long2", "label": "Cây lâu năm, súc vật làm việc và cho sản phẩm, và các tài sản cố định khác có thời gian sử dụng trên 12 tháng", "klass": "bg-cyan-600 text-white"},
]

def select_options_json(request):
    payload = list(ASSET_TYPE_OPTIONS)
    random.shuffle(payload)
    max_param = request.GET.get("max")
    if max_param is not None:
        try:
            max_value = int(max_param)
        except (TypeError, ValueError):
            max_value = None

        if max_value is not None:
            payload = payload[:max_value]

    return JsonResponse(payload, safe=False)


def dependency_max_options_json(request):
    # Simple numeric select options for the showcase (3..5).
    payload = [{"value": n, "label": str(n)} for n in range(3, 6)]
    return JsonResponse(payload, safe=False)


class UIShowcasePageView(TemplateView):
    template_name = "ui_showcase/ui_showcase.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        component = self.request.GET.get('component', 'tooltip')
        context['template_name'] = COMPONENT_TEMPLATES.get(component)
        if not context['template_name']:
            raise Http404("Unknown UI component")
        return context


def ui_showcase_delay_demo(request):
    time.sleep(3.5)
    return HttpResponse("<p class=\"text-sm text-slate-600\">Request completed.</p>")


COMPONENT_TEMPLATES = {
    "tooltip": "ui_showcase/tooltip.html",
    "button": "ui_showcase/button.html",
    "select": "ui_showcase/select.html",
    "input": "ui_showcase/input.html",
    "dropzone": "ui_showcase/dropzone.html",
    "table": "ui_showcase/table.html",
}


def ui_component_partial(request, component: str):
    template_name = COMPONENT_TEMPLATES.get(component)
    if not template_name:
        raise Http404("Unknown UI component")
    if component == "table":
        return redirect(reverse('ui_showcase_table'))
    return render(request, template_name)
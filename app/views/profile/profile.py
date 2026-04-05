from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.http import JsonResponse
from django.views import View
from django.views.generic.base import TemplateView
import json

class ProfilePageView(TemplateView):
    template_name = "profile/profile.html"


class ProfileApiView(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            msg = "Bạn cần đăng nhập để thực hiện thao tác này."
            return JsonResponse({"ok": False, "error": msg}, status=401)

        user = request.user
        profile = getattr(user, "profile", None)
        dept = getattr(profile, "department", None) if profile else None

        if user.is_superuser:
            roles = ["Quản trị viên"]
        else:
            roles = list(user.groups.values_list("name", flat=True)) or ["Thành viên"]

        payload = {
            "ok": True,
            "data": {
                "username": user.username,
                "full_name": (getattr(profile, "full_name", None) or "").strip(),
                "email": (user.email or "").strip(),
                "phone": (getattr(profile, "phone", None) or "").strip() if profile else "",
                "department": str(dept) if dept else "",
                "roles": roles,
                "is_active": bool(user.is_active),
            },
        }
        return JsonResponse(payload)

    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            msg = "Bạn cần đăng nhập để thực hiện thao tác này."
            return JsonResponse({"ok": False, "error": msg}, status=401)

        content_type = (request.content_type or "").split(";")[0].strip().lower()
        if content_type == "application/json":
            try:
                data = json.loads((request.body or b"{}").decode("utf-8"))
            except Exception:
                data = {}
        else:
            data = QueryDict(request.body or b"", encoding=request.encoding or "utf-8")

        full_name = (data.get("full_name") or "").strip()
        email = (data.get("email") or "").strip()
        phone = (data.get("phone") or "").strip()

        if not full_name or not email or not phone:
            msg = "Vui lòng nhập đầy đủ thông tin."
            return JsonResponse({"ok": False, "error": msg}, status=400)

        if "@" not in email:
            msg = "Email không hợp lệ."
            return JsonResponse({"ok": False, "error": msg}, status=400)

        user = request.user
        profile = getattr(user, "profile", None)
        if not profile:
            msg = "Không tìm thấy hồ sơ người dùng."
            return JsonResponse({"ok": False, "error": msg}, status=400)

        user.email = email
        user.save(update_fields=["email"])

        profile.full_name = full_name
        profile.phone = phone
        profile.save(update_fields=["full_name", "phone"])

        messages.success(request, "Đã lưu thay đổi thông tin cá nhân.")
        return JsonResponse({"ok": True})


class ChangePasswordApiView(View):
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            msg = "Bạn cần đăng nhập để thực hiện thao tác này."
            messages.error(request, msg)
            return JsonResponse({"ok": False, "error": msg}, status=401)

        current_password = (request.POST.get("current_password") or "").strip()
        new_password = request.POST.get("new_password") or ""
        confirm_password = request.POST.get("confirm_password") or ""

        if not current_password or not new_password or not confirm_password:
            msg = "Vui lòng nhập đầy đủ thông tin."
            messages.error(request, msg)
            return JsonResponse({"ok": False, "error": msg}, status=400)

        if not request.user.check_password(current_password):
            msg = "Mật khẩu hiện tại không đúng."
            messages.error(request, msg)
            return JsonResponse({"ok": False, "error": msg}, status=400)

        if new_password != confirm_password:
            msg = "Xác nhận mật khẩu không khớp."
            messages.error(request, msg)
            return JsonResponse({"ok": False, "error": msg}, status=400)

        try:
            validate_password(new_password, user=request.user)
        except ValidationError as exc:
            msg = exc.messages[0] if exc.messages else "Mật khẩu mới không hợp lệ."
            messages.error(request, msg)
            return JsonResponse({"ok": False, "error": msg}, status=400)

        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])
        update_session_auth_hash(request, request.user)
        messages.success(request, "Đổi mật khẩu thành công.")

        return JsonResponse({"ok": True})

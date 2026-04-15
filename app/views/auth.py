from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import FormView
from django.contrib import messages

def get_nav_items_with_permissions(user):
    all_items = [
        {
            'label': 'Tổng quan',
            'url': reverse('dashboard'),
            'icon': 'dashboard.svg',
        },
        {
            'label': 'Nhiệm vụ',
            'url': reverse('mission_list'),
            'icon': 'task.svg',
            'permissions': ['app.view_mission'],
        },
        {
            'label': 'Chỉ tiêu',
            'url': reverse('quota_list'),
            'icon': 'target.svg',
            'permissions': ['app.view_quota'],
        },
        {
            'label': 'Báo cáo', 
            'url': reverse('department_report_list'),
            'icon': 'report.svg',
            'permissions': ['app.view_departmentreport'],
        }, 
        {
            'label': 'Văn bản',
            'url': reverse('document_list'),
            'icon': 'document.svg',
            'permissions': ['app.view_document'],
        },
        # {
        #     'label': 'Người đứng đầu',
        #     'icon': 'category.svg',
        #     'children': [
        #         # {
        #         #     'label': 'Cấp chỉ đạo',
        #         #     'url': reverse('directive_level_list'),
        #         # },
        #         # {
        #         #     'label': 'Loại văn bản',
        #         #     'url': reverse('document_type_list'),
        #         # },
        #         # {
        #         #     'label': 'Văn bản chỉ đạo',
        #         #     'url': reverse('directive_document_list'),
        #         # },
        #         {
        #             'label': 'Quy định xếp loại',
        #             'url': reverse('ranking_list'),
        #         }
        #     ],
        # },
        {
            'label': 'Danh mục',
            'icon': 'category.svg',
            'children': [
                {
                    'label': 'Cấp chỉ đạo',
                    'url': reverse('directive_level_list'),
                    'permissions': ['app.view_directivelevel'],
                },
                {
                    'label': 'Loại văn bản',
                    'url': reverse('document_type_list'),
                    'permissions': ['app.view_documenttype'],
                },
                {
                    'label': 'Văn bản chỉ đạo',
                    'url': reverse('directive_document_list'),
                    'permissions': ['app.view_directivedocument'],
                },
                {
                    'label': 'Loại báo cáo theo tháng',
                    'url': reverse('report_period_month_list'),
                    'permissions': ['app.view_reportperiodmonth'],
                }
            ],
        },
        {
            'label': 'Hệ thống',
            'icon': 'setting.svg',
            'children': [
                {
                    'label': 'Người dùng',
                    'url': reverse('user_list'),
                    'permissions': ['app.view_user'],
                },
                {
                    'label': 'Đơn vị',
                    'url': reverse('department_list'),
                    'permissions': ['app.view_department'],
                },
                {
                    'label': 'Cấu hình',
                    'url': reverse('configuration_list'),
                    'permissions': ['app.view_systemconfig'],
                },
            ],
        },

    ]
    # Superuser có tất cả quyền - return tất cả items mà không cần kiểm tra permission
    if user.is_superuser:
        return all_items

    nav_items = []

    def has_any_permission(permission_keys):
        if not permission_keys:
            return True
        return any(user.has_perm(permission) for permission in permission_keys)

    def check_permission(item):
        if item.get('children'):
            children = [child for child in item['children'] if check_permission(child)]
            if not children:
                return None
            new_item = dict(item)
            new_item['children'] = children
            return new_item

        item_url = item.get('url')
        # Không có url thì fallback cho phép hiển thị item
        if not item_url:
            return item

        permission_keys = item.get('permissions', [])
        if has_any_permission(permission_keys):
            return item
        return None

    for item in all_items:
        allowed_item = check_permission(item)
        if allowed_item:
            nav_items.append(allowed_item)
    
    return nav_items


class SignInForm(forms.Form):
    username = forms.CharField(
        label='Tên đăng nhập',
        error_messages={
            'required': 'Vui lòng nhập tên đăng nhập.',
        },
    )
    password = forms.CharField(
        label='Mật khẩu',
        widget=forms.PasswordInput,
        error_messages={
            'required': 'Vui lòng nhập mật khẩu.',
        },
    )
    remember = forms.BooleanField(
        label='Ghi nhớ',
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                cleaned_data['user'] = user
                return cleaned_data
            db_user = User.objects.filter(username=username).first()
            if not db_user or db_user.is_active:
                raise forms.ValidationError("Sai tên đăng nhập hoặc mật khẩu.")
            raise forms.ValidationError("Tài khoản đã bị khoá.")
        return cleaned_data


class SignInView(FormView):
    template_name = 'sign_in.html'
    form_class = SignInForm
    success_url = reverse_lazy('dashboard')
    remember_cookie_max_age = 60 * 60 * 24 * 30

    def get_initial(self):
        initial = super().get_initial()
        remembered_username = self.request.COOKIES.get("remember_username", "")
        remembered_password = self.request.COOKIES.get("remember_password", "")
        if remembered_username:
            initial["username"] = remembered_username
        if remembered_password:
            initial["password"] = remembered_password
        initial["remember"] = bool(remembered_username or remembered_password)
        return initial

    def apply_remember_cookies(self, response, remember, username, password):
        if remember:
            response.set_cookie(
                "remember_username",
                username,
                max_age=self.remember_cookie_max_age,
                path="/",
                samesite="Lax",
            )
            response.set_cookie(
                "remember_password",
                password,
                max_age=self.remember_cookie_max_age,
                path="/",
                samesite="Lax",
            )
            return

        response.delete_cookie("remember_username", path="/", samesite="Lax")
        response.delete_cookie("remember_password", path="/", samesite="Lax")

    def get_success_url(self):
        """Lấy URL redirect từ query param 'next' nếu có và hợp lệ"""
        next_url = self.request.GET.get('next')
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts=None):
            return next_url
        return str(self.success_url)

    def dispatch(self, request, *args, **kwargs):
        # Redirect nếu user đã đăng nhập
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.cleaned_data['user']
        remember = form.cleaned_data.get('remember', False)
        password = form.cleaned_data.get('password', '')
        
        # Log the user in
        login(self.request, user)
        
        # Set session expiry based on remember me checkbox
        self.request.session.set_expiry(self.remember_cookie_max_age if remember else 0)
        
        messages.success(self.request, f'Xin chào, {user.username}!')
        # Set navbar items dựa trên permissions của user
        self.request.session["nav_items"] = get_nav_items_with_permissions(user)
        response = super().form_valid(form)
        self.apply_remember_cookies(
            response=response,
            remember=remember,
            username=user.username,
            password=password,
        )
        return response

    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context data if needed
        return context

def sign_out(request):
    logout(request)
    return redirect('root')
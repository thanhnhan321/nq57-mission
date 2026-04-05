from django.contrib.auth.models import User
from django.db.models import Case, CharField, F, Q, Value, When
from django.db.models.functions import Coalesce
from django.urls import reverse

from ....models import Department
from ...templates.components.button import Button
from ...templates.components.table import FilterParam, TableAction, TableColumn, TableContext
from .extractors import to_row
from .formatters import department_formatter, role_badge_formatter, status_badge_formatter


PAGE_TITLE = 'Người dùng'
DEFAULT_GROUP_NAME = 'Member'

COLUMNS = [
    TableColumn(name='stt', label='STT', sortable=True),
    TableColumn(name='id', label='ID', sortable=True),
    TableColumn(name='full_name', label='Họ tên', sortable=True),
    TableColumn(name='username', label='Username', sortable=True),
    TableColumn(name='email', label='Email', sortable=False),
    TableColumn(name='phone', label='Số điện thoại', sortable=False),
    TableColumn(name='department', label='Đơn vị', sortable=True, formatter=department_formatter),
    TableColumn(
        name='is_active',
        label='Trạng thái',
        sortable=True,
        type=TableColumn.Type.BOOLEAN,
        formatter=status_badge_formatter,
    ),
    TableColumn(name='role', label='Vai trò', sortable=True, formatter=role_badge_formatter),
]


def table_filters():
    return [
        FilterParam(
            name='department',
            label='Đơn vị',
            placeholder='Tất cả',
            type=FilterParam.Type.SELECT,
            extra_attributes={
                'options_url': reverse('department_options'),
            },
            query=lambda value: Q(profile__department__id=value) if value else Q(),
        ),
        FilterParam(
            name='is_active',
            label='Trạng thái',
            placeholder='Tất cả',
            type=FilterParam.Type.SELECT,
            extra_attributes={
                'options_url': reverse('user_active_status_options'),
            },
            query=lambda value: (
                Q(is_active=True) if value == 'active'
                else Q(is_active=False) if value == 'inactive'
                else Q()
            ),
        ),
        FilterParam(
            name='role',
            label='Vai trò',
            placeholder='Tất cả',
            type=FilterParam.Type.SELECT,
            extra_attributes={
                'options_url': reverse('user_role_options'),
            },
            query=lambda value: (
                Q(is_superuser=True) if value == 'admin'
                else Q(is_superuser=False) if value == 'member'
                else Q()
            ),
        ),
    ]


def table_actions():
    return [
        TableAction(
            label='Xuất danh sách',
            icon='download.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.OUTLINED,
            disabled=False,
            extra_attributes={
                'hx-get': reverse('user_export'),
                'hx-swap': 'none',
            },
        ),
        TableAction(
            label='Thêm',
            icon='plus.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.FILLED,
            disabled=False,
            extra_attributes={
                '@click': f'''$dispatch("modal:open", {{
                    url: "{reverse('user_create')}",
                    title: "Thêm mới người dùng",
                    ariaLabel: "Thêm mới người dùng",
                    closeEvent: "user:success",
                }});'''
            },
        ),
    ]


def row_actions():
    return [
        TableAction(
            label='',
            icon='edit.svg',
            icon_position=Button.IconPosition.LEFT,
            variant=Button.Variant.OUTLINED,
            disabled=False,
            extra_attributes={
                '@click': (
                    'window.dispatchEvent(new CustomEvent("modal:open", { detail: { url: "'
                    + reverse('user_update', query={'id': '__ROW_ID__'})
                    + '", title: "Cập nhật người dùng", ariaLabel: "Cập nhật người dùng", closeEvent: "user:success" } }))'
                ),
                'title': 'Cập nhật người dùng',
                'aria-label': 'Cập nhật người dùng',
            },
        ),
    ]


def get_user_table_context(request):
    table_context = TableContext(
        request=request,
        title='Danh sách người dùng',
        reload_event='user:success',
        columns=COLUMNS,
        filters=table_filters(),
        actions=table_actions(),
        row_actions=row_actions(),
        partial_url=reverse('user_list_partial'),
    )
    queryset = (
        User.objects.select_related('profile__department')
        .annotate(
            stt=F('id'),
            full_name=Coalesce('profile__full_name', 'username', output_field=CharField()),
            department=Coalesce('profile__department__short_name', 'profile__department__name', Value(''), output_field=CharField()),
            role=Case(
                When(is_superuser=True, then=Value('Quản trị viên')),
                default=Value('Thành viên'),
                output_field=CharField(),
            ),
        )
        .order_by('id')
    )
    context = table_context.to_response_context(queryset)
    start_index = context['page_index'] * context['page_size']
    context['rows'] = [
        {**to_row(row), 'stt': start_index + index + 1}
        for index, row in enumerate(context['rows'])
    ]
    return context

from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import reverse
from django.views.generic import ListView
from django.utils import timezone
from datetime import datetime, timedelta

from ..templates.components.button import Button
from ..templates.components.table import TableContext, TableAction, TableRowAction, FilterParam, TableColumn
from utils.mock import name, email, phone, address

COLUMNS = [
    TableColumn(
        name='id',
        label='ID',
        sortable=True,
    ),
    TableColumn(
        name='name',
        label='Name',
        sortable=True,
    ),
    TableColumn(
        name='email',
        label='Email',
        sortable=True,
    ),
    TableColumn(
        name='phone',
        label='Phone',
        sortable=False,
    ),
    TableColumn(
        name='address',
        label='Address',
        sortable=True,
    ),
    TableColumn(
        name='created_at',
        label='Created at',
        sortable=True,
        type=TableColumn.Type.DATETIME,
    ),
]
DATA = []
if not DATA:
    # Deterministic mock datetime range so the datetime filter is stable.
    # Stored as aware datetimes so the table column formatter can render them.
    local_tz = datetime.now().astimezone().tzinfo
    base_dt = datetime(2026, 1, 1, 10, 0, 0, tzinfo=local_tz)
    for i in range(99):
        data = {
            'id': i,
            'phone': phone(),
            'address': address(),
        }
        dt = base_dt + timedelta(days=i)
        hour = i % 24
        minute = (i * 5) % 60  # datetimepicker uses 5-minute steps by default
        dt = dt.replace(hour=hour, minute=minute)
        data['created_at'] = dt
        data['name'] = name()
        data['email'] = email(data['name'])
        DATA.append(data)

def get_common_context(request):
    table_context = TableContext(
        request=request,
        reload_event='table:reload',
        title='Table showcase',
        columns=COLUMNS,
        filters=[
            FilterParam(
                name='id',
                label='ID',
                placeholder='Select ID',
                type=FilterParam.Type.SELECT,
                inner_type=FilterParam.Type.NUMBER,
                query=lambda value: (lambda target: str(target.get('id')) == str(value)),
                extra_attributes={
                    "options_url": reverse('ui_showcase_table_id_options'),
                },
            ),
            FilterParam(
                name='name',
                label='Name',
                placeholder='Enter name',
                type=FilterParam.Type.TEXT,
                query=lambda value: (lambda target: target['name'].startswith(value)),
            ),
            FilterParam(
                name='email',
                label='Email', 
                placeholder='Enter email',
                type=FilterParam.Type.TEXT,
                query=lambda value: (lambda target: target['email'].startswith(value))
            ),
            FilterParam(
                name='phone',
                label='Phone',
                placeholder='Enter phone',
                type=FilterParam.Type.TEXT,
                query=lambda value: (lambda target: target['phone'].startswith(value))
            ),
            FilterParam(
                name='address',
                label='Address',
                placeholder='Enter address',
                type=FilterParam.Type.TEXT,
                query=lambda value: (lambda target: target['address'].startswith(value))
            ),
            FilterParam(
                name='created_since',
                label='Created since',
                placeholder='Select datetime',
                type=FilterParam.Type.DATETIME,
                query=lambda value: (lambda target: timezone.localtime(target.get('created_at')) <= timezone.localtime(datetime.fromisoformat(value))),
                extra_attributes={
                    'clearable': True,
                },
            ),
        ],
        partial_url=reverse('ui_showcase_table_partial'),
        actions=[
            TableAction(
                label='Add',
                icon='plus.svg',
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.FILLED,
                disabled=False,
                loading_text='Adding...',
                href="https://google.com",
            ),
            TableAction(
                label='Refresh',
                icon='refresh.svg',
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.OUTLINED,
                disabled=False,
                loading_text='Refreshing...',
                extra_attributes={
                    '@click': '$dispatch("table:reload")',
                },
            ),
            TableAction(
                label='Delete',
                icon='trash.svg',
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.OUTLINED,
                disabled=False,
                loading_text='Deleting...',
                extra_attributes={
                    '@click': f'''$dispatch("modal:open", 
                     {{ 
                        url: "{reverse("ui_showcase_component", kwargs={'component': 'table'})}", 
                        title: "Modal showcase",
                        ariaLabel: "Aria label" 
                    }} 
                    );'''
                }
            ),
            TableAction(
                label='Context menu',
                icon='circle.svg',
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.OUTLINED,
                disabled=False,
                extra_attributes={
                    'menu': {
                        'groups': [
                            [
                                {
                                    'label': 'Open simple modal',
                                    'icon': 'circle.svg',
                                },
                                {
                                    'label': 'Load table',
                                    'icon': 'circle.svg',
                                }
                            ],
                            [
                                {
                                'label': 'Duplicate',
                                'icon': 'circle.svg',
                                'extra_attributes': { '@click': '$dispatch("menu:duplicate")' }
                                },
                                {
                                'label': 'Archive',
                                'icon': 'circle.svg',
                                'extra_attributes': { '@click': '$dispatch("menu:archive")' }
                                }
                            ],
                            [
                                {
                                'label': 'Delete',
                                'icon': 'circle.svg',
                                'danger': True,
                                'extra_attributes': { '@click': '$dispatch("menu:delete")' }
                                }
                            ]
                        ],
                        'position': 'left',
                    }
                }
            )
        ],
        row_actions=[
            TableRowAction(
                label='Delete',
                icon='trash.svg',
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.FILLED,
                disabled=False,
                render_predicate=lambda row: row['id'] % 2 == 0,
                extra_attributes={
                    'hx-delete': f'{reverse("ui_showcase_component", kwargs={"component": "table"})}',
                }
            )
        ],
        bulk_actions=[
            TableAction(
                label='Delete',
                icon='trash.svg',
                icon_position=Button.IconPosition.LEFT,
                variant=Button.Variant.FILLED,
                disabled=False,
            )
        ]
    )
    return {
        **table_context.to_response_context(DATA),
    }

class TableListView(ListView):
    model = User
    template_name = "ui_showcase/table.html"

    def get_context_data(self, **kwargs):
        return get_common_context(self.request)

class TableListPartialView(ListView):
    model = User
    template_name = "ui_showcase/table_partial.html"

    def get_context_data(self, **kwargs):
        messages.success(self.request, 'Message from partial view index: ' + self.request.GET.get('page_index', '0'))
        return get_common_context(self.request)


def table_id_options_json(request):
    """Return table ID options for the `id` filter select."""
    options = [{"value": i, "label": str(i)} for i in range(99)]
    return JsonResponse(options, safe=False)
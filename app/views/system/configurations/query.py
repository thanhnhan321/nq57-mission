from dataclasses import dataclass
import re

from django.urls import reverse

from ....models import SystemConfig, SystemConfigHistory
from ..utils.text import normalize_text
from ...templates.components.table import TableColumn


PAGE_TITLE = 'Cấu hình thời hạn theo module'
DEFAULT_TAB = 'mission'
PAGE_SIZE_OPTIONS = (10, 25, 50)
TIME_PATTERN = re.compile(r'^(?:[01]\d|2[0-3]):[0-5]\d$')


@dataclass(frozen=True)
class ConfigFieldSpec:
    key: str
    label: str
    kind: str
    placeholder: str = ''
    minimum: int | None = None
    maximum: int | None = None


@dataclass(frozen=True)
class ConfigTabSpec:
    slug: str
    label: str
    history_prefix: str
    fields: tuple[ConfigFieldSpec, ...]


TAB_SPECS = (
    ConfigTabSpec(
        slug='mission',
        label='Nhiệm vụ',
        history_prefix='mission_',
        fields=(
            ConfigFieldSpec('mission_cutoff_day', 'Ngày chốt hàng tháng', 'number', 'Nhập số ngày', 1, 31),
            ConfigFieldSpec('mission_cutoff_time', 'Giờ chốt', 'time', 'Chọn giờ chốt'),
            ConfigFieldSpec('mission_remind_before_days', 'Số ngày nhắc nhở nộp trước', 'number', 'Nhập số ngày', 0, None),
            ConfigFieldSpec('mission_lock_after_deadline', 'Tự động khóa sau hạn', 'checkbox'),
        ),
    ),
    ConfigTabSpec(
        slug='quota',
        label='Chỉ tiêu',
        history_prefix='quota_',
        fields=(
            ConfigFieldSpec('quota_cutoff_day', 'Ngày chốt hàng tháng', 'number', 'Nhập số ngày', 1, 31),
            ConfigFieldSpec('quota_cutoff_time', 'Giờ chốt', 'time', 'Chọn giờ chốt'),
            ConfigFieldSpec('quota_remind_before_days', 'Số ngày nhắc nhở nộp trước', 'number', 'Nhập số ngày', 0, None),
            ConfigFieldSpec('quota_lock_after_deadline', 'Tự động khóa sau hạn', 'checkbox'),
        ),
    ),
    ConfigTabSpec(
        slug='report',
        label='Báo cáo',
        history_prefix='report_',
        fields=(
            ConfigFieldSpec('report_cutoff_day', 'Ngày chốt hàng tháng', 'number', 'Nhập số ngày', 1, 31),
            ConfigFieldSpec('report_cutoff_time', 'Giờ chốt', 'time', 'Chọn giờ chốt'),
            ConfigFieldSpec('report_remind_before_days', 'Số ngày nhắc nhở nộp trước', 'number', 'Nhập số ngày', 0, None),
        ),
    ),
)

TAB_BY_SLUG = {tab.slug: tab for tab in TAB_SPECS}
FIELD_BY_KEY = {field.key: field for tab in TAB_SPECS for field in tab.fields}

HISTORY_COLUMNS = [
    TableColumn(name='created_at', label='Thời điểm', width='180px', type=TableColumn.Type.DATETIME),
    TableColumn(name='updated_by', label='Người thay đổi', width='160px'),
    TableColumn(name='key_label', label='Cấu hình', width='260px'),
    TableColumn(name='value_display', label='Giá trị'),
]


def get_tabs(active_tab=DEFAULT_TAB):
    return [
        {
            'slug': tab.slug,
            'label': tab.label,
            'url': f"{reverse('configuration_partial')}?tab={tab.slug}",
        }
        for tab in TAB_SPECS
    ]


def get_configuration_page_context(request):
    return {
        'page_title': PAGE_TITLE,
        'tabs': get_tabs(DEFAULT_TAB),
        'active_tab': DEFAULT_TAB,
        'partial_url': f"{reverse('configuration_partial')}?tab={DEFAULT_TAB}",
    }


def get_configuration_tab_context(request, tab_slug, *, submitted_values=None, errors=None):
    tab_spec = get_tab_spec(tab_slug)
    page_index, page_size = get_pagination_params(request)
    current_values = load_tab_values(tab_spec)
    form_values = {**current_values, **(submitted_values or {})}
    error_map = errors or {}

    fields = [build_field_context(field, form_values.get(field.key), error_map.get(field.key)) for field in tab_spec.fields]
    field_rows = build_field_rows(fields)
    history_rows, total_count, page_index = load_history_rows(tab_spec, page_index, page_size)

    return {
        'page_title': PAGE_TITLE,
        'active_tab': tab_spec.slug,
        'tab_label': tab_spec.label,
        'tab_title': f'Cấu hình thời hạn chốt {tab_spec.label}',
        'history_title': f'Lịch sử thay đổi cấu hình {tab_spec.label}',
        'tabs': get_tabs(tab_spec.slug),
        'partial_url': f"{reverse('configuration_partial')}?tab={tab_spec.slug}",
        'fields': fields,
        'field_rows': field_rows,
        'form_values': form_values,
        'history_columns': HISTORY_COLUMNS,
        'history_rows': history_rows,
        'page_index': page_index,
        'page_size': page_size,
        'total_count': total_count,
        'errors': error_map,
        'is_editing': bool(error_map),
    }


def parse_configuration_payload(request, tab_slug):
    tab_spec = get_tab_spec(tab_slug)
    cleaned_values = {}
    errors = {}

    for field in tab_spec.fields:
        raw_value = (request.POST.get(field.key) or '').strip()

        if field.kind == 'checkbox':
            cleaned_values[field.key] = bool(request.POST.get(field.key))
            continue

        cleaned_values[field.key] = raw_value

        if not raw_value:
            errors[field.key] = f'Vui lòng nhập {field.label.lower()}.'
            continue

        if field.kind == 'time':
            if not TIME_PATTERN.match(raw_value):
                errors[field.key] = 'Giờ chốt không hợp lệ.'
            continue

        if not raw_value.isdigit():
            errors[field.key] = 'Giá trị phải là số nguyên.'
            continue

        parsed_value = int(raw_value)
        if field.minimum is not None and parsed_value < field.minimum:
            errors[field.key] = f'Giá trị phải lớn hơn hoặc bằng {field.minimum}.'
            continue
        if field.maximum is not None and parsed_value > field.maximum:
            errors[field.key] = f'Giá trị phải nhỏ hơn hoặc bằng {field.maximum}.'
            continue

        cleaned_values[field.key] = str(parsed_value)

    return cleaned_values, errors


def save_tab_values(user, tab_slug, cleaned_values):
    tab_spec = get_tab_spec(tab_slug)
    for field in tab_spec.fields:
        if field.kind == 'checkbox':
            value = 'true' if cleaned_values.get(field.key) else 'false'
        else:
            value = cleaned_values.get(field.key, '')

        config = SystemConfig.objects.filter(key=field.key).first()
        if config is None:
            config = SystemConfig(key=field.key, value=value)
            config.save(user=user)
            continue

        if config.value == value:
            continue

        config.value = value
        config.save(user=user)


def load_tab_values(tab_spec):
    values = {}
    for field in tab_spec.fields:
        values[field.key] = False if field.kind == 'checkbox' else ''

    queryset = SystemConfig.objects.filter(key__in=[field.key for field in tab_spec.fields])
    for config in queryset:
        field = FIELD_BY_KEY[config.key]
        if field.kind == 'checkbox':
            values[config.key] = str(config.value).lower() == 'true'
        else:
            values[config.key] = config.value

    return values


def load_history_rows(tab_spec, page_index, page_size):
    history_rows = list(SystemConfigHistory.objects.filter(key__startswith=tab_spec.history_prefix))

    for row in history_rows:
        field = FIELD_BY_KEY.get(row.key)
        row.key_label = field.label if field else row.key
        row.value_display = format_history_value(row.key, row.value)

    history_rows.sort(key=lambda row: row.id, reverse=True)
    history_rows.sort(key=lambda row: normalize_text(row.key_label))
    history_rows.sort(key=lambda row: row.created_at, reverse=True)

    total_count = len(history_rows)
    page_size = page_size if page_size in PAGE_SIZE_OPTIONS else PAGE_SIZE_OPTIONS[0]
    total_pages = max((total_count + page_size - 1) // page_size, 1)
    page_index = max(0, min(page_index, total_pages - 1))
    start = page_index * page_size
    end = start + page_size

    return history_rows[start:end], total_count, page_index


def get_tab_spec(tab_slug):
    return TAB_BY_SLUG.get(tab_slug, TAB_BY_SLUG[DEFAULT_TAB])


def get_pagination_params(request):
    page_index = _parse_positive_int(request.GET.get('page_index') or request.POST.get('page_index'), 0)
    page_size = _parse_positive_int(request.GET.get('page_size') or request.POST.get('page_size'), PAGE_SIZE_OPTIONS[0])
    if page_size not in PAGE_SIZE_OPTIONS:
        page_size = PAGE_SIZE_OPTIONS[0]
    return page_index, page_size


def build_field_context(field_spec, value, error_message):
    return {
        'name': field_spec.key,
        'label': field_spec.label,
        'kind': field_spec.kind,
        'placeholder': field_spec.placeholder,
        'minimum': field_spec.minimum,
        'maximum': field_spec.maximum,
        'required': field_spec.kind != 'checkbox',
        'value': value if field_spec.kind == 'checkbox' else (value or ''),
        'error_message': error_message or '',
    }


def build_field_rows(fields):
    if len(fields) == 4:
        return [fields[:2], fields[2:]]
    if len(fields) == 3:
        return [fields[:2], fields[2:]]
    return [fields]


def format_history_value(key, value):
    field = FIELD_BY_KEY.get(key)
    if field and field.kind == 'checkbox':
        return 'Có' if str(value).lower() == 'true' else 'Không'
    return value


def _parse_positive_int(value, default):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default
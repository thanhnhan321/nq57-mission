from enum import StrEnum
from typing import Any, Callable

from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.utils.dateparse import parse_date, parse_datetime
from pydantic import BaseModel, ConfigDict

import env
from ..button import Button
from .....utils.format import format_date, format_datetime, format_number, format_text

MISSING = object()
class FilterParam(BaseModel):
    class Type(StrEnum):
        SELECT = "select"
        MULTISELECT = "multiselect"
        TEXT = "text"
        NUMBER = "number"
        DATE = "date"
        DATETIME = "datetime"
        HIDDEN = "hidden"
        BOOLEAN = "boolean"
    class Option(BaseModel):
        value: Any
        label: str
    # QuerySet mode: query(value) -> Q
    # list[Any] mode: query(value) -> predicate(row) -> bool
    query: Callable[[Any], Any]
    name: str
    label: str | None = None
    placeholder: str | None = None
    hint: str | None = None
    required: bool = False
    type: Type = Type.TEXT
    inner_type: Type | None = None
    value: Any | None = MISSING
    disabled: bool = False
    error_message: str | None = None
    klass: str | None = None
    tooltip_content: str | None = None
    tooltip_axis: str = 'vertical'
    client_validate: str | None = None
    extra_attributes: dict = {}

    @staticmethod
    def __parse_value(type: Type, data: list[str] | str) -> list[Any] | Any:
        if type in [FilterParam.Type.SELECT, FilterParam.Type.MULTISELECT]:
            return data or MISSING
        if isinstance(data, list):
            return [FilterParam.__parse_value(type, item.strip()) for item in data] or MISSING
        if type == FilterParam.Type.NUMBER:
            try:
                if "." in data or "," in data:
                    return float(data)
                return int(data)
            except ValueError:
                return MISSING
        elif type == FilterParam.Type.BOOLEAN:
            if data == '':
                return MISSING
            return data == "true"
        elif type == FilterParam.Type.DATE:
            try:
                return parse_date(data) or MISSING
            except ValueError:
                return MISSING
        elif type == FilterParam.Type.DATETIME:
            try:
                return parse_datetime(data) or MISSING
            except ValueError:
                return MISSING
        return data if data else MISSING

    def extract_value(self, request: HttpRequest, **kwargs):
        if self.value is not MISSING:
            return self.value
        if self.type == FilterParam.Type.MULTISELECT:
            data = request.GET.getlist(self.name, [])
        else:
            data = request.GET.get(self.name, '').strip()
        value = self.__parse_value(self.inner_type or self.type, data)
        self.value = value if value is not MISSING else None
        return value

class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"

class PaginationParam(BaseModel):
    page_index: int
    page_size: int
    sort: str
    sort_direction: SortDirection
    filters: list[Any]

    @classmethod
    def from_table_context(cls, ctx: 'TableContext'):
        params = {
            'page_index': int(ctx.request.GET.get('page_index', '0') or 0),
            'page_size': int(ctx.request.GET.get('page_size', '10') or 10),
        }
        params['filters'] = []
        for filter in ctx.filters:
            value = filter.extract_value(ctx.request)
            if value is not MISSING:
                params['filters'].append(filter.query(value))
        params['sort'] = ''
        params['sort_direction'] = 'asc'
        sort = ctx.request.GET.get('sort', '')
        if sort and any(column.sortable for column in ctx.columns if column.name == sort):
            params['sort'] = sort
            params['sort_direction'] = ctx.request.GET.get('sort_direction', 'asc')   
        return PaginationParam(**params)

class TableColumn(BaseModel):
    class Type(StrEnum):
        TEXT = "text"
        BADGE = "badge"
        DATE = "date"
        DATETIME = "datetime"
        NUMBER = "number"
        BOOLEAN = "boolean"
        IMAGE = "image"

        @property
        def default_formatter(self):
            return {
                TableColumn.Type.DATE: lambda value: format_date(value),
                TableColumn.Type.DATETIME: lambda value: format_datetime(value),
                TableColumn.Type.NUMBER: lambda value: format_number(value),
                TableColumn.Type.TEXT: lambda value: format_text(value),
            }.get(self)

    class Align(StrEnum):
        LEFT = "left"
        CENTER = "center"
        RIGHT = "right"

    name: str
    label: str
    sortable: bool = False
    sort_fields: list[str] | None = None
    type: Type = Type.TEXT
    formatter: Callable[[Any], Any] | None = None
    is_hypertext: bool = False
    need_tooltip: bool = False
    align: Align = Align.CENTER

    
    def format(self, value: Any):
        formatter = self.formatter or self.type.default_formatter
        return formatter(value) if formatter else value

class TableAction(Button):
    pass

class TableRowAction(TableAction):
    key: str = 'id'
    render_predicate: Callable[[Any], bool] | None = None

    

class TableContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    request: HttpRequest
    title: str | None = None
    partial_url: str
    columns: list[TableColumn]
    filters: list[FilterParam] = []
    actions: list[TableAction] = []
    row_actions: list[TableRowAction] = []
    bulk_actions: list[TableAction] = []
    reload_event: str | None = None
    statistics_builder: Callable[..., str] | None = None
    show_ordinal: bool = False

    def __create_data_context(
        self,
        data_set: QuerySet | list[Any],
        params: PaginationParam,
        transformer=None,
        statistics_fields: dict | None = None,
        statistics_queryset: QuerySet | None = None,
        statistics_fn: Callable[[QuerySet], dict] | None = None,
    ):
        statistics_block = None
        if isinstance(data_set, QuerySet):
            and_filter = Q()
            for filter in params.filters:
                and_filter &= filter
            # Lấy ordering hiện tại TRƯỚC KHI filter (nếu có)
            # Đây là ordering mặc định từ query_set ban đầu (ví dụ: từ Meta.ordering hoặc order_by trong query)
            default_sort = []
            # Kiểm tra xem query_set có ordering không
            if hasattr(data_set.query, 'order_by') and data_set.query.order_by:
                default_sort = list((
                    exp if isinstance(exp, str) else 
                    f"{'-' if exp.descending else ''}{exp.expression.name}"
                    for exp in data_set.query.order_by 
                ))
            data_set = data_set.filter(and_filter)

            if statistics_fn is not None:
                stats_qs = (
                    statistics_queryset.filter(and_filter)
                    if statistics_queryset is not None
                    else data_set
                )
                statistics = statistics_fn(stats_qs)
                statistics_block = self.statistics_builder(statistics) if self.statistics_builder else None
            elif statistics_fields:
                stats_qs = (
                    statistics_queryset.filter(and_filter)
                    if statistics_queryset is not None
                    else data_set
                )
                statistics = stats_qs.aggregate(**statistics_fields)
                statistics_block = self.statistics_builder(statistics) if self.statistics_builder else None

            if params.sort:
                user_sort = ("-" if params.sort_direction == SortDirection.DESC else "") + params.sort
                # Tránh duplicate: chỉ thêm nếu chưa có trong default_order
                user_sort_normalized = user_sort.lstrip("-")
                duplicate_sort = next((sort for sort in default_sort if sort.lstrip("-") == user_sort_normalized), None)
                if duplicate_sort:
                    # Thêm sort của user ra trước ordering mặc định
                    default_sort.remove(duplicate_sort)
                final_sort = [user_sort] + default_sort if default_sort else [user_sort]
                data_set = data_set.order_by(*final_sort) if final_sort else data_set
            else:
                # Nếu không có sort từ user, giữ nguyên ordering mặc định
                if default_sort:
                    data_set = data_set.order_by(*default_sort)
            
            total_count = data_set.count()
            page_rows = data_set.all()[params.page_index* params.page_size : (params.page_index + 1) * params.page_size]
            for index, row in enumerate(page_rows):
                if self.show_ordinal:
                    row["ordinal"] = index + 1 + params.page_index * params.page_size
                if transformer:
                    row = transformer(row)
        else:
            # Filter is partially supported for list[Any]
            for filter in params.filters:
                data_set = [row for row in data_set if filter(row)]
            data_set = sorted(data_set, key=lambda x: x[params.sort], reverse=params.sort_direction == SortDirection.DESC) if params.sort else data_set
            total_count = len(data_set)
            page_rows = data_set[params.page_index* params.page_size : (params.page_index + 1) * params.page_size]
            for index, row in enumerate(page_rows):
                if self.show_ordinal:
                    row["ordinal"] = index + 1 + params.page_index * params.page_size
                if transformer:
                    row = transformer(row)
        return {
            'total_count': total_count,
            'rows': page_rows,
            'page_index': params.page_index,
            'page_size': params.page_size,
            'sort': params.sort,
            'sort_direction': params.sort_direction,
            'statistics_block': statistics_block,
            'data_set': data_set,
        }

    def to_response_context(
        self,
        data_set: QuerySet | list[Any],
        transformer: Callable[[Any], Any] | None = None,
        statistics_fields: dict | None = None,
        statistics_queryset: QuerySet | None = None,
        statistics_fn: Callable[[QuerySet], dict] | None = None,
    ):
        params = PaginationParam.from_table_context(self)
        data_context = self.__create_data_context(
            data_set,
            params,
            transformer,
            statistics_fields,
            statistics_queryset=statistics_queryset,
            statistics_fn=statistics_fn,
        )
        if self.show_ordinal:
            self.columns.insert(0, TableColumn(name="ordinal", label="STT", type=TableColumn.Type.NUMBER))
        build_context = {
            name: getattr(self, name) for name in self.__class__.model_fields
        }
        return {**build_context, **data_context}

from uuid import uuid4
import re
from django.contrib.messages import get_messages
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from jinja2 import Environment

from utils.json import jsonify





def environment(**options):
    env = Environment(**options)
    def get_attribute(object, key, default=None):
        """Get item from dictionary by key"""
        if isinstance(object, dict):
            return object.get(key, default)
        return getattr(object, key, default)
    def substitute_row_attrs(attrs, row, key='id'):
        """
        Replace placeholder tokens in string values used for row actions.

        Supported placeholders:
        - `__ROW_ID__`: replaced with `row[key]` (where `key` is the filter arg, default `id`)
        - `__<field>__`: replaced with `row[<field>]` (e.g. `__quota_id__`, `__department_id__`)
        """
        if not attrs:
            return attrs
        rid = str(get_attribute(row, key, ""))
        token_re = re.compile(r"__(?P<name>[A-Za-z0-9_]+)__")
        # Replace any `__field__` tokens with the corresponding attribute from `row`.
        # Note: `__ROW_ID__` is treated as a special-case.
        def replace_token(match: re.Match[str]) -> str:
            name = match.group("name")
            if name == "ROW_ID":
                return rid
            return str(get_attribute(row, name, ""))

        if isinstance(attrs, str):
            return token_re.sub(replace_token, attrs)
        out = {}
        for k, v in attrs.items():
            if not isinstance(v, str):
                out[k] = v
                continue
            out[k] = token_re.sub(replace_token, v)  
        return out

    env.globals.update(
        {
            "static": staticfiles_storage.url,
            "url": reverse,
            "jsonify": jsonify,
            "get_attribute": get_attribute,
            "get_messages": get_messages,
            "uuid": uuid4,
        }
    )
    env.filters["substitute_row_attrs"] = substitute_row_attrs

    return env

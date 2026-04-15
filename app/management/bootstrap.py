from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.apps import apps
from django.core import serializers
from django.contrib.auth.models import Group, User
from django.core.management.color import no_style
from django.db import connection, transaction

from app.management.auth_seed import MEMBER_GROUP_NAME, ensure_member_group
from app.management.user_seed import get_seed_department_usernames, seed_department_users
from app.models import (
    Department,
    DepartmentReport,
    DirectiveDocument,
    Document,
    Storage,
    SystemConfig,
    SystemConfigHistory,
    ReportPeriodMonth,
)


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
FIXTURE_FILES = [
    "department_sample.json",
    "reportmonth.json",
    "system_config_sample.json",
]


@dataclass(slots=True)
class BootstrapResult:
    fixture_records: int = 0
    auth_groups: int = 0
    auth_permissions: int = 0
    users: int = 0
    profiles: int = 0
    report_months: int = 0
    system_configs: int = 0
    deleted_records: int = 0


def load_fixture_file(file_name: str) -> int:
    path = FIXTURE_DIR / file_name
    raw_objects = json.loads(path.read_text(encoding="utf-8"))
    filtered_objects = []
    for item in raw_objects:
        model_label = item["model"].split(".", 1)
        if len(model_label) != 2:
            continue

        app_label, model_name = model_label
        try:
            model_class = apps.get_model(app_label, model_name)
        except LookupError:
            continue

        allowed_fields = {field.name for field in model_class._meta.concrete_fields}
        allowed_fields.update(field.name for field in model_class._meta.many_to_many)
        filtered_fields = {
            field_name: field_value
            for field_name, field_value in item["fields"].items()
            if field_name in allowed_fields
        }
        filtered_objects.append(
            {
                "model": item["model"],
                "pk": item.get("pk"),
                "fields": filtered_fields,
            }
        )

    if not filtered_objects:
        return 0

    payload = json.dumps(filtered_objects, ensure_ascii=False)
    loaded = 0
    for deserialized_object in serializers.deserialize("json", payload):
        deserialized_object.save()
        loaded += 1
    return loaded


def load_fixture_bundle() -> int:
    loaded = 0
    for file_name in FIXTURE_FILES:
        loaded += load_fixture_file(file_name)
    return loaded


def reset_model_sequences(*models) -> None:
    sql_statements = connection.ops.sequence_reset_sql(no_style(), models)
    if not sql_statements:
        return

    with connection.cursor() as cursor:
        for statement in sql_statements:
            cursor.execute(statement)


def clear_bootstrap_data() -> int:
    deleted = 0
    seed_usernames = get_seed_department_usernames(include_inactive=True)
    if seed_usernames:
        deleted += User.objects.filter(username__in=seed_usernames).delete()[0]

    for model in (
        DepartmentReport,
        DirectiveDocument,
        Document,
        Storage,
        ReportPeriodMonth,
        SystemConfig,
        SystemConfigHistory,
    ):
        deleted += model.objects.count()
        model.objects.all().delete()
    return deleted


def _bootstrap_initial_data() -> BootstrapResult:
    result = BootstrapResult()
    result.fixture_records = load_fixture_bundle()
    reset_model_sequences(Department)
    auth_result = ensure_member_group()
    result.auth_groups = auth_result.groups
    result.auth_permissions = auth_result.permissions
    member_group = Group.objects.get(name=MEMBER_GROUP_NAME)
    seed_result = seed_department_users(member_group)
    result.users = seed_result.users
    result.profiles = seed_result.profiles
    return result


def bootstrap_initial_data() -> BootstrapResult:
    with transaction.atomic():
        return _bootstrap_initial_data()


def reset_and_bootstrap_data(interactive: bool = True) -> BootstrapResult | None:
    if interactive:
        answer = input("Bạn có chắc chắn muốn xoá dữ liệu khởi tạo và nạp lại? (yes/no): ")
        if answer.strip().lower() != "yes":
            return None

    with transaction.atomic():
        deleted = clear_bootstrap_data()
        result = _bootstrap_initial_data()
        result.deleted_records = deleted
        return result

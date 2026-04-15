from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import transaction

from app.management.bootstrap import reset_model_sequences
from app.management.user_seed import ensure_user_profile, get_catp_department
from app.models import Department


CSV_FILE_NAME = "department.csv"
DEFAULT_CSV_PATH = Path(__file__).resolve().parent.parent / "fixtures" / CSV_FILE_NAME
PARENT_DEPARTMENT_NAME = "Công an TP.HCM"
PARENT_DEPARTMENT_SHORT_NAME = "CATP"
PARENT_DEPARTMENT_TYPE = Department.Type.CAP
DEPARTMENT_NAME_COLUMN = "Tên đơn vị"
SHORT_NAME_COLUMN = "Tên viết tắt"
GROUP_COLUMN = "Nhóm đơn vị"
DEFAULT_ADMIN_USERNAME = "admin"


@dataclass(slots=True)
class DepartmentImportResult:
    total_rows: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0


def import_departments_from_csv(csv_path: str | Path | None = None) -> DepartmentImportResult:
    resolved_path = Path(csv_path) if csv_path else DEFAULT_CSV_PATH
    if not resolved_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file CSV: {resolved_path}")

    admin_user = _get_admin_user()
    reset_model_sequences(Department)
    parent_department = _ensure_parent_department(admin_user)
    result = DepartmentImportResult()

    with resolved_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        _validate_columns(reader.fieldnames or [])

        with transaction.atomic():
            for row in reader:
                department_name = _normalize_value(row.get(DEPARTMENT_NAME_COLUMN))
                if not department_name:
                    result.skipped += 1
                    continue

                department_type = _normalize_department_type(row.get(GROUP_COLUMN))
                short_name = _normalize_value(row.get(SHORT_NAME_COLUMN)) or None

                department = Department.objects.filter(name=department_name).first()
                is_create = department is None
                if is_create:
                    department = Department(name=department_name)

                department.short_name = short_name
                department.type = department_type
                department.parent = parent_department
                department.save(user=admin_user)

                result.total_rows += 1
                if is_create:
                    result.created += 1
                else:
                    result.updated += 1

    return result


def _get_admin_user():
    user_model = get_user_model()
    admin_user, created = user_model.objects.get_or_create(
        username=DEFAULT_ADMIN_USERNAME,
        defaults={"first_name": "Admin", "last_name": "System", "email": ""},
    )
    if created:
        admin_user.set_unusable_password()
        admin_user.save(update_fields=["password"])
    ensure_user_profile(
        admin_user,
        get_catp_department(),
        full_name=admin_user.get_full_name() or admin_user.username,
        update_existing=True,
    )
    return admin_user


def _ensure_parent_department(admin_user):
    parent_department = Department.objects.filter(name=PARENT_DEPARTMENT_NAME).first()
    if parent_department is None:
        parent_department = Department(name=PARENT_DEPARTMENT_NAME)

    parent_department.short_name = PARENT_DEPARTMENT_SHORT_NAME
    parent_department.type = PARENT_DEPARTMENT_TYPE
    parent_department.parent = None
    parent_department.save(user=admin_user)
    return parent_department


def _normalize_value(value: str | None) -> str:
    return (value or "").strip()


def _normalize_department_type(value: str | None) -> str:
    normalized = _normalize_value(value).upper()
    if normalized not in Department.Type.values:
        raise ValueError(f"Nhóm đơn vị không hợp lệ: {value!r}")
    return normalized


def _validate_columns(fieldnames: list[str]) -> None:
    required_columns = {DEPARTMENT_NAME_COLUMN, SHORT_NAME_COLUMN, GROUP_COLUMN}
    missing_columns = sorted(required_columns - set(fieldnames))
    if missing_columns:
        raise ValueError(f"Thiếu cột bắt buộc trong CSV: {', '.join(missing_columns)}")

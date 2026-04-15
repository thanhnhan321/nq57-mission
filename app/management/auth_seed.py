from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.contrib.auth.models import Group, Permission, User
from django.db import transaction

from app.management.user_seed import ensure_user_profile, get_catp_department


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
MEMBER_GROUP_NAME = "Member"
MEMBER_GROUP_SEED_FILE = FIXTURE_DIR / "member_group_seed.json"


@dataclass(slots=True)
class AuthBootstrapResult:
    groups: int = 0
    permissions: int = 0
    memberships: int = 0
    profiles: int = 0


def _load_member_group_seed() -> dict:
    data = json.loads(MEMBER_GROUP_SEED_FILE.read_text(encoding="utf-8"))
    groups = data.get("groups") or []
    for group in groups:
        if group.get("name") == MEMBER_GROUP_NAME:
            return group
    raise ValueError(f"Không tìm thấy cấu hình group {MEMBER_GROUP_NAME!r} trong {MEMBER_GROUP_SEED_FILE}")


MEMBER_PERMISSION_CODENAMES = tuple(_load_member_group_seed().get("permissions") or [])


def _resolve_permissions(permission_codenames: list[str]) -> list[Permission]:
    permissions: list[Permission] = []
    missing_codenames: list[str] = []

    for permission_code in permission_codenames:
        try:
            app_label, codename = permission_code.split(".", 1)
        except ValueError as exc:
            raise ValueError(f"Permission code không hợp lệ: {permission_code!r}") from exc

        permission = Permission.objects.filter(
            content_type__app_label=app_label,
            codename=codename,
        ).first()
        if permission is None:
            missing_codenames.append(permission_code)
            continue
        permissions.append(permission)

    if missing_codenames:
        raise LookupError(
            "Thiếu permission trong database: {codes}".format(codes=", ".join(sorted(missing_codenames)))
        )

    return permissions


@transaction.atomic
def ensure_member_group() -> AuthBootstrapResult:
    permissions = _resolve_permissions(list(MEMBER_PERMISSION_CODENAMES))
    group, created = Group.objects.get_or_create(name=MEMBER_GROUP_NAME)
    current_permission_ids = set(group.permissions.values_list("id", flat=True))
    expected_permission_ids = {permission.id for permission in permissions}

    if current_permission_ids != expected_permission_ids:
        group.permissions.set(permissions)

    return AuthBootstrapResult(
        groups=1 if created else 0,
        permissions=len(permissions),
    )


@transaction.atomic
def sync_superusers_to_member_group() -> AuthBootstrapResult:
    group_result = ensure_member_group()
    member_group = Group.objects.get(name=MEMBER_GROUP_NAME)
    catp_department = get_catp_department()
    memberships = 0
    profiles = 0

    for user in User.objects.filter(is_superuser=True):
        if not user.groups.filter(id=member_group.id).exists():
            user.groups.add(member_group)
            memberships += 1

        if ensure_user_profile(user, catp_department, update_existing=False):
            profiles += 1

    return AuthBootstrapResult(
        groups=group_result.groups,
        permissions=group_result.permissions,
        memberships=memberships,
        profiles=profiles,
    )

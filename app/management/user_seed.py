from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import Group, User

from app.models import Department, UserProfile


DEFAULT_SEEDED_PASSWORD = "Abc@12345"
CATP_SHORT_NAME = "CATP"


@dataclass(slots=True)
class UserSeedResult:
    users: int = 0
    profiles: int = 0


def get_seed_departments(active_only: bool = True) -> list[Department]:
    departments = Department.objects.exclude(parent__isnull=True).order_by("id")
    if active_only:
        departments = departments.filter(is_active=True)
    departments = departments.exclude(short_name__isnull=True).exclude(short_name="")
    return list(departments)


def get_seed_department_usernames(include_inactive: bool = False) -> list[str]:
    return [
        _department_username(department)
        for department in get_seed_departments(active_only=not include_inactive)
    ]


def get_catp_department() -> Department:
    department = Department.objects.filter(short_name__iexact=CATP_SHORT_NAME).first()
    if department is None:
        raise LookupError(f"Không tìm thấy đơn vị {CATP_SHORT_NAME!r}")
    return department


def seed_department_users(
    member_group: Group,
    default_password: str = DEFAULT_SEEDED_PASSWORD,
) -> UserSeedResult:
    result = UserSeedResult()
    for department in get_seed_departments():
        user = ensure_department_user(
            department,
            member_group,
            default_password=default_password,
        )
        ensure_user_profile(
            user,
            department,
            full_name=department.name,
            update_existing=True,
        )
        result.users += 1
        result.profiles += 1
    return result


def ensure_department_user(
    department: Department,
    member_group: Group,
    default_password: str = DEFAULT_SEEDED_PASSWORD,
) -> User:
    username = _department_username(department)
    user = User.objects.filter(username__iexact=username).first()

    if user is None:
        user = User(username=username)
        user.email = ""
        user.is_staff = True
        user.is_superuser = False
        user.is_active = True
        user.set_password(default_password)
        user.save()
    else:
        changed_fields: list[str] = []
        if user.username != username:
            if User.objects.filter(username=username).exclude(pk=user.pk).exists():
                raise ValueError(f"Tên đăng nhập đã tồn tại: {username}")
            user.username = username
            changed_fields.append("username")

        if user.email != "":
            user.email = ""
            changed_fields.append("email")

        if not user.is_staff:
            user.is_staff = True
            changed_fields.append("is_staff")

        if user.is_superuser:
            user.is_superuser = False
            changed_fields.append("is_superuser")

        if not user.is_active:
            user.is_active = True
            changed_fields.append("is_active")

        if changed_fields:
            user.save(update_fields=changed_fields)

    user.groups.add(member_group)
    return user


def ensure_user_profile(
    user: User,
    department: Department,
    *,
    full_name: str | None = None,
    phone: str | None = None,
    update_existing: bool = False,
) -> bool:
    resolved_full_name = _resolve_full_name(user, full_name)
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "department": department,
            "full_name": resolved_full_name,
            "phone": phone,
        },
    )
    if created:
        return True

    if not update_existing:
        return False

    update_fields: list[str] = []
    if profile.department_id != department.id:
        profile.department = department
        update_fields.append("department")

    if profile.full_name != resolved_full_name:
        profile.full_name = resolved_full_name
        update_fields.append("full_name")

    if phone is not None and profile.phone != phone:
        profile.phone = phone
        update_fields.append("phone")

    if update_fields:
        profile.save(update_fields=update_fields)

    return False


def _department_username(department: Department) -> str:
    short_name = (department.short_name or "").strip()
    if not short_name:
        raise ValueError(f"Đơn vị {department.pk} không có short_name")
    return short_name.lower()


def _resolve_full_name(user: User, full_name: str | None) -> str:
    if full_name is not None:
        return full_name

    resolved_full_name = user.get_full_name().strip()
    return resolved_full_name or user.username

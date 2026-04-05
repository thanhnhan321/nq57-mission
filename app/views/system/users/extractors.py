from django.core.exceptions import ObjectDoesNotExist


def get_full_name(user):
    try:
        profile = user.profile
    except ObjectDoesNotExist:
        profile = None

    if profile and (profile.full_name or '').strip():
        return profile.full_name.strip()

    full_name = (user.get_full_name() or '').strip()
    return full_name or user.username


def get_role(user):
    if user.is_superuser:
        return 'Quản trị viên'
    return 'Thành viên'


def get_phone(user):
    profile = getattr(user, 'profile', None)
    phone = (getattr(profile, 'phone', None) or '').strip() if profile else ''
    return phone or '—'


def get_department_label(user):
    profile = getattr(user, 'profile', None)
    department = getattr(profile, 'department', None) if profile else None
    return str(department) if department else '—'


def to_row(user):
    return {
        'id': user.id,
        'full_name': get_full_name(user),
        'username': user.username,
        'email': (user.email or '').strip(),
        'phone': get_phone(user),
        'department': get_department_label(user),
        'is_active': user.is_active,
        'role': get_role(user),
    }

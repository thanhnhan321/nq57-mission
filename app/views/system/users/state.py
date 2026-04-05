from django.contrib.auth.models import Group


def apply_default_user_state(user, group_name):
    user.is_staff = True
    member_group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(member_group)


def apply_role_state(user, is_admin):
    user.is_staff = True
    user.is_superuser = is_admin
    user.save(update_fields=['is_staff', 'is_superuser'])

from django.core.management.base import BaseCommand

from app.management.auth_seed import sync_superusers_to_member_group


class Command(BaseCommand):
    help = "Đồng bộ group Member cho các superuser"

    def handle(self, *args, **options):
        result = sync_superusers_to_member_group()
        self.stdout.write(
            self.style.SUCCESS(
                "Đã đảm bảo group Member có {permissions} quyền, gắn thêm {memberships} superuser vào group và đồng bộ {profiles} user_profile.".format(
                    permissions=result.permissions,
                    memberships=result.memberships,
                    profiles=result.profiles,
                )
            )
        )

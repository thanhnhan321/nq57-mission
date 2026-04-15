from django.core.management.base import BaseCommand

from app.management.bootstrap import reset_and_bootstrap_data


class Command(BaseCommand):
    help = "Xoá dữ liệu bootstrap rồi nạp lại"

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            action="store_false",
            dest="interactive",
            default=True,
            help="Bỏ qua bước xác nhận trước khi xoá dữ liệu",
        )

    def handle(self, *args, **options):
        result = reset_and_bootstrap_data(interactive=options["interactive"])
        if result is None:
            self.stdout.write(self.style.WARNING("Đã huỷ thao tác."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                "Đã xoá {deleted_records} bản ghi và nạp lại {fixture_records} bản ghi fixture, đảm bảo group Member và {auth_permissions} quyền, đồng bộ {users} user đơn vị, {profiles} user_profile, {report_months} kỳ báo cáo và {system_configs} cấu hình hệ thống.".format(
                    deleted_records=result.deleted_records,
                    fixture_records=result.fixture_records,
                    auth_permissions=result.auth_permissions,
                    users=result.users,
                    profiles=result.profiles,
                    report_months=result.report_months,
                    system_configs=result.system_configs,
                )
            )
        )

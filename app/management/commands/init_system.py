from django.core.management.base import BaseCommand

from app.management.bootstrap import bootstrap_initial_data, reset_and_bootstrap_data


class Command(BaseCommand):
    help = "Khởi tạo hệ thống dữ liệu cho ứng dụng"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Xoá dữ liệu bootstrap trước khi nạp lại",
        )
        parser.add_argument(
            "--noinput",
            action="store_false",
            dest="interactive",
            default=True,
            help="Bỏ qua bước xác nhận nếu dùng cùng --reset",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            result = reset_and_bootstrap_data(interactive=options["interactive"])
            if result is None:
                self.stdout.write(self.style.WARNING("Đã huỷ thao tác."))
                return

            self.stdout.write(
                self.style.SUCCESS(
                    "Đã reset {deleted_records} bản ghi và nạp lại {fixture_records} bản ghi fixture.".format(
                        deleted_records=result.deleted_records,
                        fixture_records=result.fixture_records,
                    )
                )
            )
            return

        result = bootstrap_initial_data()
        self.stdout.write(
            self.style.SUCCESS(
                "Đã khởi tạo {fixture_records} bản ghi fixture, đảm bảo group Member và {auth_permissions} quyền, đồng bộ {users} user đơn vị, {profiles} user_profile, {report_months} kỳ báo cáo và {system_configs} cấu hình hệ thống.".format(
                    fixture_records=result.fixture_records,
                    auth_permissions=result.auth_permissions,
                    users=result.users,
                    profiles=result.profiles,
                    report_months=result.report_months,
                    system_configs=result.system_configs,
                )
            )
        )

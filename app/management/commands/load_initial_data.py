from django.core.management.base import BaseCommand

from app.management.bootstrap import bootstrap_initial_data


class Command(BaseCommand):
    help = "Nạp dữ liệu khởi tạo cho ứng dụng"

    def handle(self, *args, **options):
        result = bootstrap_initial_data()
        self.stdout.write(
            self.style.SUCCESS(
                "Đã nạp {fixture_records} bản ghi fixture, đảm bảo group Member và {auth_permissions} quyền, đồng bộ {users} user đơn vị, {profiles} user_profile, {report_months} kỳ báo cáo và {system_configs} cấu hình hệ thống.".format(
                    fixture_records=result.fixture_records,
                    auth_permissions=result.auth_permissions,
                    users=result.users,
                    profiles=result.profiles,
                    report_months=result.report_months,
                    system_configs=result.system_configs,
                )
            )
        )

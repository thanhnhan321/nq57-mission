from pathlib import Path

from django.core.management.base import BaseCommand

from app.management.department_csv import DEFAULT_CSV_PATH, import_departments_from_csv


class Command(BaseCommand):
    help = "Import dữ liệu Department từ file CSV thật"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-path",
            default=str(DEFAULT_CSV_PATH),
            help="Đường dẫn CSV nguồn (mặc định là file fixtures thật)",
        )

    def handle(self, *args, **options):
        result = import_departments_from_csv(Path(options["csv_path"]))
        self.stdout.write(
            self.style.SUCCESS(
                "Đã import {total_rows} dòng, tạo {created} Department, cập nhật {updated}, bỏ qua {skipped}.".format(
                    total_rows=result.total_rows,
                    created=result.created,
                    updated=result.updated,
                    skipped=result.skipped,
                )
            )
        )

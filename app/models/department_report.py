from django.db import models

from .base import AuditModel
from .department import Department
from .storage import Storage
from .period import Period


class DepartmentReport(AuditModel):
    class ReportType(models.TextChoices):
        MONTH = "MONTH", "Báo cáo tháng"
        QUARTER = "QUARTER", "Báo cáo quý"
        HALF_YEAR = "HALF_YEAR", "Báo cáo 6 tháng"
        NINE_MONTH = "NINE_MONTH", "Báo cáo 9 tháng"
        YEAR = "YEAR", "Báo cáo năm"

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="department_reports",
        db_column="department_id",
    )

    month = models.PositiveSmallIntegerField(null=True, blank=True)
    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
        null=True,
        blank=True,
    )
    report_year = models.PositiveSmallIntegerField()

    file = models.ForeignKey(
        Storage,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="department_reports",
        db_column="file_object_uid",
    )

    file_name = models.CharField(max_length=255, null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=50, default="NOT_SENT")
    note = models.TextField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)

    period = models.ForeignKey(
        Period,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='period_department_report'
    )

    class Meta:
        db_table = "department_report"
        constraints = [
            models.CheckConstraint(
                check=models.Q(month__gte=1, month__lte=12),
                name="ck_department_report_month_range",
            ),
            models.UniqueConstraint(
                fields=["department", "month", "report_type", "report_year"],
                name="uq_department_report",
            ),
        ]
        ordering = ["-report_year", "month", "department_id"]

    def save(self, *args, **kwargs):
        if self.file and not self.file_name:
            self.file_name = self.file.file_name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.department} - {self.month:02d}/{self.report_year} - {self.report_type}"
from django.db import models

class ReportPeriodMonth(models.Model):
    class ReportType(models.TextChoices):
        MONTH = "MONTH", "Báo cáo tháng"
        QUARTER = "QUARTER", "Báo cáo quý"
        HALF_YEAR = "HALF_YEAR", "Báo cáo 6 tháng"
        NINE_MONTH = "NINE_MONTH", "Báo cáo 9 tháng"
        YEAR = "YEAR", "Báo cáo năm"
    month = models.PositiveSmallIntegerField()

    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
    )

    class Meta:
        db_table = "report_period_month"
        constraints = [
            models.UniqueConstraint(
                fields=["month", "report_type"],
                name="uq_month_type"
            )
        ]
        ordering = ["month"]

    def __str__(self):
        return f"Tháng {self.month} - {self.report_type}"

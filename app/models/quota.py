from django.db import models
from django.db.models.fields import uuid
from django.utils.translation import gettext_lazy as label

from .base import AuditModel
from .department import Department
from .period import Period

class Quota(AuditModel):

    class Type(models.TextChoices):
        CUMULATIVE = ("cumulative", label("Số liệu tại thời điểm báo cáo"))
        DISCRETE = ("discrete", label("Số liệu trong kỳ báo cáo"))
        
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=255)
    type = models.CharField(
        max_length=20,
        choices=Type.choices
    )
    register_guide = models.TextField()
    submit_guide = models.TextField()
    target_percent = models.FloatField()
    issued_at = models.DateField()
    expired_at = models.DateField()

    class Meta:
        db_table = "quota"
        ordering = ["-issued_at"]

    def __str__(self):
        return self.name

class QuotaAssignment(AuditModel):
    quota = models.ForeignKey(
        Quota,
        on_delete=models.PROTECT,
        related_name="department_assignments",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="quota_assignments",
    )
    is_leader = models.BooleanField(db_index=True)

    class Meta:
        db_table = "quota_assignment"

    def __str__(self):
        return f"{self.quota.name} - {self.department.short_name} - {'Lãnh đạo' if self.is_leader else 'Thực hiện'}"

class QuotaReport(AuditModel):
    class Status(models.TextChoices):
        NOT_SENT = ("not_sent", label("Chưa gửi"))
        PENDING = ("pending", label("Chờ duyệt"))
        REJECTED = ("rejected", label("Từ chối"))
        FAILED = ("failed", label("Không đạt"))
        PASSED = ("passed", label("Đạt"))

        @property
        def color(self):
            return {
                QuotaReport.Status.NOT_SENT: "gray",
                QuotaReport.Status.PENDING: "yellow",
                QuotaReport.Status.REJECTED: "gray",
                QuotaReport.Status.FAILED: "red",
                QuotaReport.Status.PASSED: "green",
            }.get(self.value, "gray")

    quota = models.ForeignKey(
        Quota,
        on_delete=models.PROTECT,
        related_name="department_reports",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="quota_reports",
    )
    period = models.ForeignKey(
        Period,
        on_delete=models.PROTECT,
        related_name="quota_reports",
    )
    expected_value = models.BigIntegerField(null=True)
    actual_value = models.BigIntegerField(null=True)
    note = models.TextField(null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        db_index=True,
    )
    version = models.PositiveSmallIntegerField(default=1)
    submit_at = models.DateTimeField(null=True)
    submit_by = models.CharField(max_length=512, null=True)
    reviewed_at = models.DateTimeField(null=True)
    reviewed_by = models.CharField(max_length=512, null=True)
    reason = models.TextField(null=True)

    class Meta:
        db_table = "quota_report"
        constraints = [
            models.UniqueConstraint(
                fields=["quota", "department", "period"],
                name="uq_quota_report",
            ),
        ]

    def __str__(self):
        return f"{self.quota.name} - {self.department.short_name} - {self.status}"
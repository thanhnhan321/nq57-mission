from django.db import models
from django.contrib.auth.models import User
from .department import Department
from .document import DirectiveDocument
from .period import Period


class Mission(models.Model):
    code = models.CharField(max_length=50, primary_key=True)
    # Mã nhiệm vụ, vd: VBCD_001

    name = models.TextField()
    # Tên nhiệm vụ

    description = models.TextField(blank=True, null=True)
    # Mô tả chi tiết nhiệm vụ

    directive_document = models.ForeignKey(
        DirectiveDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='missions'
    )
    # Văn bản chỉ đạo
    # 1 văn bản có thể thuộc nhiều nhiệm vụ
    # 1 nhiệm vụ chỉ có 1 văn bản

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        related_name='missions'
    )
    # Đơn vị chủ trì

    assignee_departments = models.ManyToManyField(
        Department,
        blank=True,
        related_name='assigned_missions'
    )
    # Đơn vị thực hiện

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_missions'
    )
    # Người phụ trách chính

    start_date = models.DateField(null=True, blank=True)
    # Ngày bắt đầu

    due_date = models.DateField(null=True, blank=True)
    # Thời hạn

    completed_date = models.DateField(null=True, blank=True)
    # Ngày hoàn thành

    progress = models.PositiveSmallIntegerField(default=0)
    # % tiến độ, 0-100

    result_summary = models.TextField(blank=True, null=True)
    # Kết quả

    is_active = models.BooleanField(default=True)
    # Soft delete

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_missions'
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_missions'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mission'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.name}"

class MissionReport(models.Model):
    class Status(models.TextChoices):
        NOT_SENT = "NOT_SENT", "Chưa gửi"
        APPROVED = "APPROVED", "Đã gửi"
        # NO_REPORT = "NO_REPORT", "Không gửi"

    class MissionStatus(models.TextChoices):
        IN_PROGRESS_ON_TIME = "IN_PROGRESS_ON_TIME", "Đang thực hiện đúng hạn"
        IN_PROGRESS_LATE = "IN_PROGRESS_LATE", "Đang thực hiện trễ hạn"
        COMPLETED_ON_TIME = "COMPLETED_ON_TIME", "Hoàn thành đúng hạn"
        COMPLETED_LATE = "COMPLETED_LATE", "Hoàn thành trễ hạn"
        NOT_COMPLETED_LATE = "NOT_COMPLETED_LATE", "Chưa thực hiện trễ hạn"
        NOT_COMPLETED_ON_TIME = "NOT_COMPLETED_ON_TIME", "Chưa thực hiện đúng hạn"

    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    # Nhiệm vụ nào

    report_month = models.PositiveSmallIntegerField()
    # Kỳ báo cáo - tháng

    report_year = models.PositiveSmallIntegerField()
    # Kỳ báo cáo - năm

    content = models.TextField(blank=True, null=True)
    # Nội dung báo cáo

    no_work_generated = models.BooleanField(default=False)
    # Không có phát sinh báo cáo trong tháng

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_SENT
    )
    # Tình trạng báo cáo
    mission_status = models.CharField(
        max_length=30,
        choices=MissionStatus.choices,
        default=MissionStatus.NOT_COMPLETED_ON_TIME
    )
    # Thời điểm gửi
    is_sent = models.BooleanField(default=False, null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_mission_reports'
    )

    is_locked = models.BooleanField(default=False, null=True, blank=True)
    # Khóa chỉnh sửa sau khi duyệt hoặc quá hạn

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    period = models.ForeignKey(
        Period,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='period_mission'
    )

    class Meta:
        db_table = 'mission_report'
        unique_together = ('mission', 'report_month', 'report_year')
        ordering = ['-report_year', '-report_month', '-created_at']

    def save(self, *args, **kwargs):
        # Keep status consistent with period/deadline + sent flags.
        self.is_locked = self.status in (self.Status.APPROVED, self.Status.NO_REPORT)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.mission.code} - {self.report_month:02d}/{self.report_year}"

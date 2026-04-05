from django.core.exceptions import ValidationError
from django.db import models

from .base import AuditModel


class SystemConfig(models.Model):
    class Key(models.TextChoices):
        MISSION_CUTOFF_DAY = ("mission_cutoff_day", "Nhiệm vụ - ngày chốt hàng tháng")
        MISSION_CUTOFF_TIME = ("mission_cutoff_time", "Nhiệm vụ - giờ chốt")
        MISSION_LOCK_AFTER_DEADLINE = ("mission_lock_after_deadline", "Nhiệm vụ - tự động khóa")
        MISSION_REMIND_BEFORE_DAYS = ("mission_remind_before_days", "Nhiệm vụ - nhắc nhở nộp")
        QUOTA_CUTOFF_DAY = ("quota_cutoff_day", "Chỉ tiêu - ngày chốt hàng tháng")
        QUOTA_CUTOFF_TIME = ("quota_cutoff_time", "Chỉ tiêu - giờ chốt")
        QUOTA_LOCK_AFTER_DEADLINE = ("quota_lock_after_deadline", "Chỉ tiêu - tự động khóa")
        QUOTA_REMIND_BEFORE_DAYS = ("quota_remind_before_days", "Chỉ tiêu - nhắc nhở nộp")
        REPORT_CUTOFF_DAY = ("report_cutoff_day", "Báo cáo - ngày chốt hàng tháng")
        REPORT_CUTOFF_TIME = ("report_cutoff_time", "Báo cáo - giờ chốt")
        REPORT_REMIND_BEFORE_DAYS = ("report_remind_before_days", "Báo cáo - nhắc nhở nộp")

    key = models.TextField(primary_key=True, choices=Key.choices)
    value = models.TextField()

    class Meta:
        db_table = "system_config"
        ordering = ["key"]

    def __str__(self):
        return self.key

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._loaded_key = instance.key
        return instance

    def clean(self):
        super().clean()
        if self.key not in self.Key.values:
            raise ValidationError({"key": "Key cấu hình không hợp lệ."})

        if self._state.adding:
            return

        if getattr(self, "_loaded_key", self.key) != self.key:
            raise ValidationError({"key": "Không được đổi key sau khi tạo."})

    def save(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        is_create = self._state.adding
        original_value = None

        if not is_create and getattr(self, "_loaded_key", self.key) != self.key:
            self.full_clean()

        if not is_create:
            original = type(self).objects.only("value").get(pk=getattr(self, "_loaded_key", self.key))
            original_value = original.value

        self.full_clean()
        super().save(*args, **kwargs)

        if is_create or original_value != self.value:
            self._create_history(user=user)

        self._loaded_key = self.key

    def _create_history(self, user=None):
        history = SystemConfigHistory(key=self.key, value=self.value)
        if user is None:
            history.created_by = "system"
            history.updated_by = "system"
            history.save()
            return

        history.save(user=user)


class SystemConfigHistory(AuditModel):
    key = models.TextField(choices=SystemConfig.Key.choices)
    value = models.TextField()

    class Meta:
        db_table = "system_config_history"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.key
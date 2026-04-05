from django.db import models
from django.contrib.auth.models import User

from .base import AuditModel
class Department(AuditModel):
    class Type(models.TextChoices):
        CAP = "CAP"
        CAX = "CAX"

    short_name = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=Type.choices, default=Type.CAX)
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        related_name='children',
        db_column='parent_id'
    )

    class Meta:
        db_table = 'department'
        ordering = ['id', 'name']

    def get_short_label(self) -> str:
        """Hiển thị ưu tiên short_name (bảng/chi tiết); thiếu thì dùng name."""
        s = (self.short_name or "").strip()
        return s or self.name

    def __str__(self):
        return self.short_name or self.name

class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='users'
    )

    class Meta:
        db_table = 'user_profile'

    def __str__(self):
        return self.full_name or self.user.username
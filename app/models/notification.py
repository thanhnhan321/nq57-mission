from django.db import models
from django.contrib.auth.models import User

from .base import AuditModel

class Notification(AuditModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    url = models.CharField(max_length=255)
